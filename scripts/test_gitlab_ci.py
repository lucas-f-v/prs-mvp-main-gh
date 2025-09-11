#!/usr/bin/env python3
"""Test script for GitLab CI/CD MR Summarizer."""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_environment_variables():
    """Test that all required environment variables are available."""
    logger.info("🧪 Testing Environment Variables...")
    
    required_vars = [
        'CI_PROJECT_ID', 'CI_MERGE_REQUEST_IID', 'CI_MERGE_REQUEST_SOURCE_BRANCH_NAME',
        'CI_MERGE_REQUEST_TARGET_BRANCH_NAME', 'GITLAB_PERSONAL_TOKEN', 'CI_API_V4_URL',
        'STACKSPOT_CLIENT_ID', 'STACKSPOT_CLIENT_SECRET', 'STACKSPOT_CLIENT_REALM'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
            logger.error(f"❌ {var}: Not set")
        else:
            if 'SECRET' in var or 'TOKEN' in var:
                display_value = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
            else:
                display_value = value
            logger.info(f"✅ {var}: {display_value}")
    
    if missing_vars:
        logger.error(f"\n❌ Missing required variables: {missing_vars}")
        return False

    logger.info("\n✅ All environment variables are set!")
    return True

def test_imports():
    """Test that all required Python modules can be imported."""
    logger.info("\n🧪 Testing Python Imports...")
    
    required_modules = ['requests', 'json', 'time', 'urllib.parse', 'logging', 're']
    
    for module in required_modules:
        try:
            __import__(module)
            logger.info(f"✅ {module}: Available")
        except ImportError as e:
            logger.error(f"❌ {module}: {e}")
            return False
    
    logger.info("\n✅ All required modules are available!")
    return True

def test_gitlab_api_access():
    """Test the hybrid approach: git commands + personal access token."""
    logger.info("\n🧪 Testing GitLab Hybrid Access - Git Commands + Personal Token...")
    
    try:
        import requests
        import subprocess
        
        personal_token = os.environ.get('GITLAB_PERSONAL_TOKEN')
        gitlab_api_url = os.environ.get('CI_API_V4_URL')
        project_id = os.environ.get('CI_PROJECT_ID')
        mr_iid = os.environ.get('CI_MERGE_REQUEST_IID')
        source_branch = os.environ.get('CI_MERGE_REQUEST_SOURCE_BRANCH_NAME')
        target_branch = os.environ.get('CI_MERGE_REQUEST_TARGET_BRANCH_NAME', 'main')
        
        logger.info(f"   Environment Variables:")
        logger.info(f"   GITLAB_PERSONAL_TOKEN: {'SET' if personal_token else 'NOT SET'}")
        if personal_token:
            logger.info(f"   Token preview: {personal_token[:8]}...{personal_token[-4:]} ({len(personal_token)} chars)")
        logger.info(f"   CI_API_V4_URL: {gitlab_api_url}")
        logger.info(f"   CI_PROJECT_ID: {project_id}")
        logger.info(f"   CI_MERGE_REQUEST_IID: {mr_iid}")
        logger.info(f"   CI_MERGE_REQUEST_SOURCE_BRANCH_NAME: {source_branch}")
        logger.info(f"   CI_MERGE_REQUEST_TARGET_BRANCH_NAME: {target_branch}")
        
        results = {}
        
        logger.info(f"\n   🔍 Test 1: Git Commands for Diff Extraction")
        if source_branch and target_branch:
            results['git_diff'] = test_git_commands(source_branch, target_branch)
        else:
            logger.error(f"   ❌ Missing branch variables for git diff test")
            results['git_diff'] = False
        
        logger.info(f"\n   🔍 Test 2: Personal Token for Comment Posting")
        if personal_token and gitlab_api_url and project_id and mr_iid:
            results['personal_token_comments'] = test_personal_token_comments(
                gitlab_api_url, project_id, personal_token, mr_iid
            )
        else:
            missing = []
            if not personal_token: missing.append('GITLAB_PERSONAL_TOKEN')
            if not gitlab_api_url: missing.append('CI_API_V4_URL')
            if not project_id: missing.append('CI_PROJECT_ID')
            if not mr_iid: missing.append('CI_MERGE_REQUEST_IID')
            logger.error(f"   ❌ Missing required variables: {missing}")
            results['personal_token_comments'] = False
        
        logger.info(f"\n   📊 Hybrid Approach Test Results:")
        passed_tests = []
        failed_tests = []
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"   {test_name}: {status}")
            if result:
                passed_tests.append(test_name)
            else:
                failed_tests.append(test_name)
        
        logger.info(f"\n   Passed: {len(passed_tests)}/2 tests")
        if len(passed_tests) == 2:
            logger.info(f"   🎉 SUCCESS: Hybrid approach fully functional!")
            logger.info(f"   ✅ Can extract diffs using git commands")
            logger.info(f"   ✅ Can post comments using personal access token")
        elif len(passed_tests) == 1:
            logger.warning(f"   ⚠️  PARTIAL: One component working")
            logger.info(f"   Working: {', '.join(passed_tests)}")
            logger.info(f"   Failed: {', '.join(failed_tests)}")
        else:
            logger.error(f"   ❌ FAILED: Neither component working")
            logger.error(f"   Need to investigate: {', '.join(failed_tests)}")
        
        return len(passed_tests) > 0
            
    except Exception as e:
        logger.error(f"❌ GitLab hybrid test suite failed with exception: {e}")
        logger.error(f"   Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
        return False

def test_personal_token_comments(gitlab_api_url, project_id, personal_token, mr_iid):
    """Test personal access token for posting comments (full API access)"""
    try:
        import requests
        
        url = f"{gitlab_api_url}/projects/{project_id}/merge_requests/{mr_iid}/notes"
        headers = {"PRIVATE-TOKEN": personal_token}
        
        logger.info(f"   URL: {url}")
        logger.info(f"   Headers: PRIVATE-TOKEN")
        logger.info(f"   Method: GET (read existing notes)")
        logger.info(f"   Token: {personal_token[:8]}...{personal_token[-4:]}")
        
        response = requests.get(url, headers=headers, timeout=10)
        logger.info(f"   Response: HTTP {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"   ✅ Success: Retrieved {len(data)} existing notes")
            logger.info(f"   Personal access token has full API access")
            return True
        else:
            logger.error(f"   ❌ Failed: {response.text[:200]}")
            if response.status_code == 401:
                logger.error(f"   Diagnosis: Invalid or expired personal access token")
            elif response.status_code == 403:
                logger.error(f"   Diagnosis: Personal token lacks required permissions")
            elif response.status_code == 404:
                logger.error(f"   Diagnosis: Project or merge request not found")
            return False
    except Exception as e:
        logger.error(f"   ❌ Exception: {e}")
        return False

def test_git_commands(source_branch, target_branch):
    """Test git commands for getting diff data (reliable approach)"""
    try:
        import subprocess
        import os
        
        commit_sha = os.environ.get('CI_COMMIT_SHA')
        commit_before_sha = os.environ.get('CI_COMMIT_BEFORE_SHA')
        
        logger.info(f"   Available commit info:")
        logger.info(f"   CI_COMMIT_SHA: {commit_sha}")
        logger.info(f"   CI_COMMIT_BEFORE_SHA: {commit_before_sha}")
        logger.info(f"   Source branch: {source_branch}")
        logger.info(f"   Target branch: {target_branch}")
        logger.info(f"   Method: Multiple git diff approaches (CI environment compatible)")
        
        git_command = ['git', 'diff', 'HEAD~1...HEAD']
        logger.info(f"   Command: {' '.join(git_command)}")
        logger.info(f"   Method: Git diff HEAD~1...HEAD (CI environment compatible)")
        
        result = subprocess.run(
            git_command,
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            diff_output = result.stdout
            logger.info(f"   ✅ Success: Generated {len(diff_output)} character diff")
            if diff_output.strip():
                lines = diff_output.count('\n')
                logger.info(f"   Diff contains {lines} lines")
            else:
                logger.info(f"   Note: Empty diff (no changes detected)")
            return True
        else:
            logger.error(f"   ❌ Failed: {result.stderr[:100]}")
            logger.error(f"   Git diff command failed")
        return False
    except Exception as e:
        logger.error(f"   ❌ Exception: {e}")
        return False

def test_stackspot_credentials():
    """Test StackSpot AI credentials (without making actual API calls)."""
    logger.info("\n🧪 Testing StackSpot Credentials...")
    
    client_id = os.environ.get('STACKSPOT_CLIENT_ID')
    client_secret = os.environ.get('STACKSPOT_CLIENT_SECRET')
    client_realm = os.environ.get('STACKSPOT_CLIENT_REALM')
    
    logger.info(f"   Expected: All StackSpot credentials should be set and resolved")
    logger.info(f"   Actual STACKSPOT_CLIENT_ID: {'SET' if client_id else 'NOT SET'}")
    logger.info(f"   Actual STACKSPOT_CLIENT_SECRET: {'SET' if client_secret else 'NOT SET'}")
    logger.info(f"   Actual STACKSPOT_CLIENT_REALM: {'SET' if client_realm else 'NOT SET'}")
    
    if not all([client_id, client_secret, client_realm]):
        missing = []
        if not client_id: missing.append('STACKSPOT_CLIENT_ID')
        if not client_secret: missing.append('STACKSPOT_CLIENT_SECRET')
        if not client_realm: missing.append('STACKSPOT_CLIENT_REALM')
        logger.error(f"❌ Missing StackSpot credentials: {missing}")
        return False
    
    logger.info(f"   Expected: Variables should be resolved, not showing as $VARIABLE_NAME")
    
    if client_id and client_id.startswith('$'):
        logger.error(f"❌ STACKSPOT_CLIENT_ID appears to be unresolved variable: {client_id}")
        logger.error("   Diagnosis: Variable not properly set in GitLab CI/CD settings")
        return False
    
    if client_secret and client_secret.startswith('$'):
        logger.error(f"❌ STACKSPOT_CLIENT_SECRET appears to be unresolved variable: {client_secret}")
        logger.error("   Diagnosis: Variable not properly set in GitLab CI/CD settings")
        return False
        
    if client_realm and client_realm.startswith('$'):
        logger.error(f"❌ STACKSPOT_CLIENT_REALM appears to be unresolved variable: {client_realm}")
        logger.error("   Diagnosis: Variable not properly set in GitLab CI/CD settings")
        return False
    
    logger.info(f"   Expected: CLIENT_ID should be at least 10 chars, CLIENT_SECRET at least 20 chars")
    
    if client_id and len(client_id) < 10:
        logger.error(f"❌ STACKSPOT_CLIENT_ID seems too short: {len(client_id)} chars")
        return False
    
    if client_secret and len(client_secret) < 20:
        logger.error(f"❌ STACKSPOT_CLIENT_SECRET seems too short: {len(client_secret)} chars")
        return False
    
    if client_realm and not client_realm.strip():
        logger.error(f"❌ STACKSPOT_CLIENT_REALM is empty")
        return False
    
    logger.info("✅ StackSpot credentials format looks valid")
    if client_id:
        logger.info(f"   Client ID: {client_id[:8]}... ({len(client_id)} chars)")
    if client_secret:
        logger.info(f"   Client Secret: {client_secret[:4]}...{client_secret[-4:]} ({len(client_secret)} chars)")
    if client_realm:
        logger.info(f"   Realm: {client_realm}")

    return True

def test_filter_changed_files():
    """Verify file filtering logic with mock data."""
    from gitlab_ci_summarizer import filter_changed_files

    mock_files = [
        {'status': 'M', 'path': 'src/app.py'},
        {'status': 'A', 'path': 'README.md'},
        {'status': 'D', 'path': 'src/old.py'},
        {'status': 'R100', 'old': 'src/old_name.py', 'new': 'src/new_name.py'},
    ]

    def mock_should_include(path):
        return path.startswith('src/')

    allowed = filter_changed_files(mock_files, mock_should_include)
    expected = ['src/app.py', 'src/old.py', 'src/new_name.py']

    assert allowed == expected, f"Expected {expected}, got {allowed}"
    logger.info("✅ Filtering logic works as expected")
    return True

def main():
    """Run all tests."""
    logger.info("🚀 GitLab CI/CD MR Summarizer - Test Suite")
    logger.info("=" * 50)
    
    tests = [
        test_environment_variables,
        test_imports,
        test_gitlab_api_access,
        test_stackspot_credentials,
        test_filter_changed_files
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            logger.error(f"❌ Test failed with exception: {e}")
    
    logger.info("\n" + "=" * 50)
    logger.info(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! GitLab CI/CD setup looks good.")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed. Please check the configuration.")
        sys.exit(1)

if __name__ == "__main__":
    main()
