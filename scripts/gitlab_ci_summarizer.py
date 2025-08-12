#!/usr/bin/env python3
"""GitLab CI/CD MR Summarizer - Simplified version without AWS dependencies."""

import os
import sys
import requests
from json import dumps, loads
from time import sleep
from urllib.parse import quote_plus
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STK_AUTH_BASE_URL = "https://idm.stackspot.com"
STK_AI_API_BASE_URL = "https://genai-code-buddy-api.stackspot.com/v1"
RQC_PARTIAL_SUMMARY_SLUG = "partial-summary"
RQC_TOTAL_SUMMARY_SLUG = "total-summary"
MAX_RQC_INPUT_SIZE_BYTES = 50000  # 50KB limit for RQC inputs

RQC_STATUS_COMPLETED = "COMPLETED"
RQC_STATUS_FAILED = "FAILED"
RQC_TIMEOUT_MINUTES = 15
RQC_SECONDS_TO_WAIT = 10
RQC_TIMEOUT_LIMIT = int((RQC_TIMEOUT_MINUTES * 60) / RQC_SECONDS_TO_WAIT)

class StackSpotAIError(Exception):
    """Custom exception for StackSpot AI errors."""
    pass

class RQCExecutionTimeoutError(Exception):
    """Custom exception for RQC execution timeouts."""
    pass

def get_gitlab_mr_diff():
    """Get the GitLab MR diff using git commands - reliable approach."""
    import subprocess
    
    source_branch = os.environ.get('CI_MERGE_REQUEST_SOURCE_BRANCH_NAME')
    target_branch = os.environ.get('CI_MERGE_REQUEST_TARGET_BRANCH_NAME', 'main')
    mr_iid = os.environ.get('CI_MERGE_REQUEST_IID')
    
    logger.info(f"Fetching diff for MR {mr_iid} using git commands")
    logger.info(f"Source branch: {source_branch}")
    logger.info(f"Target branch: {target_branch}")
    logger.info(f"Method: Git commands (reliable, no API limitations)")
    
    if not source_branch:
        logger.error("CI_MERGE_REQUEST_SOURCE_BRANCH_NAME not available")
        raise ValueError("Source branch name required for git diff")
    
    commit_sha = os.environ.get('CI_COMMIT_SHA')
    commit_before_sha = os.environ.get('CI_COMMIT_BEFORE_SHA')
    
    logger.info(f"CI_COMMIT_SHA: {commit_sha}")
    logger.info(f"CI_COMMIT_BEFORE_SHA: {commit_before_sha}")
    
    git_command = ['git', 'diff', 'HEAD~1...HEAD']
    logger.info(f"Using git command: {' '.join(git_command)}")
    logger.info(f"Method: Git diff HEAD~1...HEAD (CI environment compatible)")
    
    try:
        result = subprocess.run(
            git_command,
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            errors='replace',
            timeout=60,
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Git diff successful")
            logger.info(f"Git command return code: {result.returncode}")
            
            diff_content = result.stdout
            diff_content = validate_encoding(diff_content)
            logger.info(f"Retrieved diff with {len(diff_content)} characters")
            logger.info(f"Diff encoding validated, size: {len(diff_content)} chars")
            
            if not diff_content.strip():
                logger.warning("Empty diff - no changes between branches")
                return ""
            
            lines = diff_content.count('\n')
            logger.info(f"Diff contains {lines} lines")
            
            return diff_content.strip()
        else:
            logger.error(f"❌ Git command failed (code {result.returncode}): {result.stderr[:200]}")
            raise ValueError("Git diff command failed in CI environment")
            
    except FileNotFoundError:
        logger.error("Git command not found. Ensure git is installed in CI environment.")
        logger.error("Check .gitlab-ci.yml before_script includes: apt-get update && apt-get install -y git")
        raise ValueError("Git not available in CI environment")
    except subprocess.TimeoutExpired:
        logger.error("❌ Git command timed out")
        raise ValueError("Git diff command timed out")
    except Exception as e:
        logger.error(f"❌ Git command exception: {e}")
        raise ValueError(f"Git diff failed with exception: {e}")

def post_gitlab_mr_comment(comment_body):
    """Post a comment to the GitLab MR using personal access token."""
    project_id = os.environ['CI_PROJECT_ID']
    mr_iid = os.environ['CI_MERGE_REQUEST_IID']
    gitlab_token = os.environ['GITLAB_PERSONAL_TOKEN']
    gitlab_api_url = os.environ['CI_API_V4_URL']
    
    logger.info(f"Posting comment to MR {mr_iid} in project {project_id}")
    
    comment_body = validate_encoding(comment_body)
    comment_body = sanitize_for_json(comment_body)
    comment_body = validate_comment_size(comment_body)
    
    logger.info(f"Comment length: {len(comment_body)} characters")
    logger.info(f"Comment size: {len(comment_body.encode('utf-8'))} bytes")
    logger.info(f"Using GITLAB_PERSONAL_TOKEN: {gitlab_token[:8]}...{gitlab_token[-4:]}")
    logger.info(f"Authentication method: Personal Access Token (full API access)")
    
    notes_url = f"{gitlab_api_url}/projects/{project_id}/merge_requests/{mr_iid}/notes"
    headers = {"PRIVATE-TOKEN": gitlab_token, "Content-Type": "application/json"}
    data = {"body": comment_body}
    
    logger.info(f"Making request to: {notes_url}")
    logger.info(f"Request headers: {{'PRIVATE-TOKEN': '{gitlab_token[:8]}...{gitlab_token[-4:]}', 'Content-Type': 'application/json'}}")
    logger.info(f"Expected: HTTP 200/201 response for successful comment posting")
    
    response = requests.post(notes_url, headers=headers, json=data)
    
    logger.info(f"Response status: {response.status_code}")
    logger.info(f"Response headers: {dict(response.headers)}")
    
    if response.status_code not in [200, 201]:
        logger.error(f"Failed to post MR comment: {response.status_code}")
        logger.error(f"Response body: {response.text[:500]}")
        if response.status_code == 401:
            logger.error("Diagnosis: 401 = Authentication failed with GITLAB_PERSONAL_TOKEN")
        elif response.status_code == 403:
            logger.error("Diagnosis: 403 = GITLAB_PERSONAL_TOKEN lacks permissions to post comments")
        elif response.status_code == 404:
            logger.error("Diagnosis: 404 = Merge request not found or project access denied")
    
    response.raise_for_status()
    
    logger.info("Successfully posted comment to MR")
    return response.json()

def get_stackspot_access_token():
    """Get StackSpot AI access token."""
    client_id = os.environ['STACKSPOT_CLIENT_ID']
    client_secret = os.environ['STACKSPOT_CLIENT_SECRET']
    client_realm = os.environ['STACKSPOT_CLIENT_REALM']
    
    url = f"{STK_AUTH_BASE_URL}/{client_realm}/oidc/oauth/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    
    token_data = response.json()
    logger.info("Successfully obtained StackSpot access token")
    return token_data["access_token"]

def stackspot_make_request(method, url, body=None, retries=3):
    """Make authenticated request to StackSpot AI API."""
    for attempt in range(retries + 1):
        try:
            access_token = get_stackspot_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=body or {})
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if attempt < retries and e.response.status_code in [401, 403, 500, 503]:
                logger.info(f"Got status code {e.response.status_code} on attempt {attempt}, retrying...")
                sleep(2**(attempt+1))
                continue
            raise

def create_rqc_execution(qc_slug, input_data):
    """Create a StackSpot RQC execution."""
    url = f"{STK_AI_API_BASE_URL}/quick-commands/create-execution/{qc_slug}"
    body = {"input_data": input_data}
    
    logger.info(f"Creating RQC execution for {qc_slug}")
    response_data = stackspot_make_request("POST", url, body)
    
    execution_id = response_data
    logger.info(f"Created RQC execution with ID: {execution_id}")
    return execution_id

def poll_rqc_execution(execution_id):
    """Poll for RQC execution result."""
    url = f"{STK_AI_API_BASE_URL}/quick-commands/callback/{execution_id}"
    
    execution_time = 0
    for attempt in range(RQC_TIMEOUT_LIMIT):
        response_data = stackspot_make_request("GET", url)
        
        if response_data and "progress" in response_data:
            status = response_data["progress"]["status"]
        else:
            logger.error(f"Invalid response data: {response_data}")
            return None
        logger.debug(f"Polling attempt {attempt}: status = {status}")
        
        if status == RQC_STATUS_COMPLETED:
            logger.info(f"RQC execution completed in ~{execution_time} seconds")
            if "result" in response_data:
                return response_data["result"]
            else:
                logger.error(f"No result in completed response: {response_data}")
                return None
        
        if status == RQC_STATUS_FAILED:
            logger.error(f"RQC execution failed: {response_data}")
            raise StackSpotAIError(f"RQC execution failed: {response_data}")
        
        execution_time += RQC_SECONDS_TO_WAIT
        sleep(RQC_SECONDS_TO_WAIT)
    
    raise RQCExecutionTimeoutError(f"RQC execution timed out after {RQC_TIMEOUT_MINUTES} minutes")

def run_rqc(qc_slug, input_data, retries=1):
    """Execute a StackSpot RQC and get result."""
    for attempt in range(retries + 1):
        try:
            execution_id = create_rqc_execution(qc_slug, input_data)
            result = poll_rqc_execution(execution_id)
            return result
        except RQCExecutionTimeoutError:
            if attempt < retries:
                logger.info(f"RQC execution timed out, retrying... (attempt {attempt + 1})")
                continue
            logger.error("RQC execution failed due to timeout")
            raise
        except StackSpotAIError:
            logger.error("RQC execution failed due to StackSpot AI error")
            raise

def split_diff(diff):
    """Split complete diff into per-file diffs."""
    import re
    
    diff_blocks = re.split(r'(?=^diff --git)', diff, flags=re.MULTILINE)
    diff_blocks = [block.strip() for block in diff_blocks if block.strip()]
    
    logger.info(f"Split diff into {len(diff_blocks)} file diffs")
    return diff_blocks

def string_size_in_bytes(string):
    """Get UTF-8 byte size of string."""
    return len(string.encode('utf-8'))

def string_is_too_large(string):
    """Check if string exceeds RQC input size limit."""
    return string_size_in_bytes(string) > MAX_RQC_INPUT_SIZE_BYTES

def validate_encoding(text, encoding='utf-8'):
    """Validate and normalize text encoding."""
    try:
        if isinstance(text, bytes):
            return text.decode(encoding, errors='replace')
        return text.encode(encoding, errors='replace').decode(encoding)
    except Exception as e:
        logger.warning(f"Encoding validation failed: {e}")
        return text.encode('ascii', errors='replace').decode('ascii')

def sanitize_for_json(text):
    """Sanitize text for safe JSON serialization."""
    import json
    try:
        json.dumps(text)
        return text
    except (UnicodeDecodeError, TypeError):
        logger.warning("Text contains invalid unicode, sanitizing...")
        return text.encode('utf-8', errors='replace').decode('utf-8')

def validate_comment_size(comment_body):
    """Validate GitLab comment size and truncate if needed."""
    comment_size_bytes = len(comment_body.encode('utf-8'))
    if comment_size_bytes > 1048576:  # 1MB GitLab limit
        logger.warning(f"Comment too large ({comment_size_bytes} bytes), truncating...")
        return comment_body[:1048000] + "\n\n... (truncated due to size limit)"
    return comment_body

def simplify_file_diff(file_diff):
    """Simplify large file diff by removing details."""
    import re
    
    simplified_diff = re.sub(
        r'(@@.*?@@)(.*?)(?=(^diff --git|\Z))',
        r'\1\n{Changes are too large to process and have been omitted}\n',
        file_diff,
        flags=re.DOTALL | re.MULTILINE
    )
    
    return simplified_diff

def prepare_file_diffs(file_diffs):
    """Batch file diffs optimally for RQC processing."""
    joint_diffs = []
    current_joint_diff = ""
    
    for index, file_diff in enumerate(file_diffs):
        file_diff_simplified = file_diff
        
        if string_is_too_large(file_diff):
            file_diff_simplified = simplify_file_diff(file_diff)
            logger.info(f"Simplified large file diff (original size: {string_size_in_bytes(file_diff)} bytes)")
        
        if string_is_too_large(current_joint_diff + file_diff_simplified):
            if current_joint_diff:  # Don't append empty string
                joint_diffs.append(current_joint_diff)
            current_joint_diff = file_diff_simplified
        else:
            current_joint_diff += file_diff_simplified
        
        if index == len(file_diffs) - 1:
            joint_diffs.append(current_joint_diff)
    
    joint_diffs_sizes = [string_size_in_bytes(diff) for diff in joint_diffs]
    logger.info(f"Created {len(joint_diffs)} batched diffs with sizes: {joint_diffs_sizes} bytes")
    
    return joint_diffs

def get_partial_summary_inputs(diff):
    """Get batched inputs for partial summary RQCs."""
    file_diffs = split_diff(diff)
    inputs = prepare_file_diffs(file_diffs)
    return inputs

def strip_response(response):
    """Strip code block formatting from response."""
    import re
    
    response = response.strip()
    
    if response.startswith("```"):
        response = re.sub(r'^```[a-zA-Z0-9{}]*\s*\n?', '', response)
    
    if response.endswith("```"):
        response = response[:-3]
    
    return response

def parse_json_response(response):
    """Parse JSON response from StackSpot AI."""
    if not (response := strip_response(response)):
        return {}
    
    response = validate_encoding(response)
    response = sanitize_for_json(response)
    
    try:
        parsed_response = loads(response)
        logger.info(f"Parsed StackSpot response: {parsed_response}")
        return parsed_response
    except Exception as e:
        logger.error(f"Failed to parse JSON response: {e}")
        return {}

def get_partial_summaries(diff):
    """Get partial summaries for all files in diff."""
    inputs = get_partial_summary_inputs(diff)
    
    partial_summaries = []
    
    for i, input_data in enumerate(inputs):
        logger.info(f"Processing partial summary batch {i + 1}/{len(inputs)}")
        
        try:
            partial_summary_response = run_rqc(RQC_PARTIAL_SUMMARY_SLUG, input_data)
            partial_summary = parse_json_response(partial_summary_response)
            
            if partial_summary:
                if isinstance(partial_summary, list):
                    partial_summaries.extend(partial_summary)
                else:
                    partial_summaries.append(partial_summary)
        except Exception as e:
            logger.error(f"Failed to get partial summary for batch {i + 1}: {e}")
            continue
    
    logger.info(f"Generated {len(partial_summaries)} partial summaries")
    return partial_summaries

def get_total_summary(partial_summaries):
    """Get total summary from partial summaries."""
    logger.info("Generating total summary from partial summaries")
    
    try:
        comment_response = run_rqc(RQC_TOTAL_SUMMARY_SLUG, dumps(partial_summaries))
        comment = strip_response(comment_response)
        return comment
    except Exception as e:
        logger.error(f"Failed to generate total summary: {e}")
        return "❌ **Failed to generate AI summary**\n\nThere was an error processing the merge request changes with StackSpot AI. Please review the changes manually."

def main():
    """Main function to process GitLab MR and generate AI summary."""
    try:
        required_vars = [
            'CI_PROJECT_ID', 'CI_MERGE_REQUEST_IID', 'CI_MERGE_REQUEST_SOURCE_BRANCH_NAME',
            'CI_MERGE_REQUEST_TARGET_BRANCH_NAME', 'GITLAB_PERSONAL_TOKEN', 'CI_API_V4_URL',
            'STACKSPOT_CLIENT_ID', 'STACKSPOT_CLIENT_SECRET', 'STACKSPOT_CLIENT_REALM'
        ]
        
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            logger.error("Expected: All variables should be set in GitLab CI/CD settings")
            for var in missing_vars:
                logger.error(f"  {var}: {'SET' if os.environ.get(var) else 'NOT SET'}")
            sys.exit(1)
        
        logger.info("Environment variables check:")
        logger.info("Note: Using git commands + GITLAB_PERSONAL_TOKEN (GitLab.com Free tier compatible)")
        for var in required_vars:
            value = os.environ.get(var, '')
            if 'TOKEN' in var or 'SECRET' in var:
                if value:
                    logger.info(f"  {var}: SET ({value[:8]}...{value[-4:]}) - {len(value)} chars")
                    if value.startswith('$'):
                        logger.error(f"  WARNING: {var} appears to be unresolved variable: {value}")
                else:
                    logger.info(f"  {var}: NOT SET")
            else:
                logger.info(f"  {var}: {value if value else 'NOT SET'}")
                if value and value.startswith('$'):
                    logger.error(f"  WARNING: {var} appears to be unresolved variable: {value}")
        
        logger.info("Starting GitLab MR summarizer")
        
        diff = get_gitlab_mr_diff()
        
        if not diff.strip():
            logger.info("No changes found in MR, skipping summary generation")
            return
        
        partial_summaries = get_partial_summaries(diff)
        
        if not partial_summaries:
            logger.warning("No partial summaries generated, posting fallback comment")
            comment = "📝 **AI Summary**\n\nNo significant changes detected for summary generation."
        else:
            comment = get_total_summary(partial_summaries)
        
        post_gitlab_mr_comment(comment)
        
        logger.info("Successfully completed MR summarization")
        
    except Exception as e:
        logger.error(f"Failed to process MR: {e}")
        
        try:
            error_comment = f"❌ **AI Summary Failed**\n\nThere was an error generating the AI summary: `{str(e)}`\n\nPlease review the changes manually."
            post_gitlab_mr_comment(error_comment)
        except:
            logger.error("Failed to post error comment to MR")
        
        sys.exit(1)

if __name__ == "__main__":
    main()
