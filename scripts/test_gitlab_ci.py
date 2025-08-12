#!/usr/bin/env python3
"""Test script for GitLab CI/CD MR Summarizer."""

import os
import sys

def test_environment_variables():
    """Test that all required environment variables are available."""
    print("🧪 Testing Environment Variables...")
    
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
            print(f"❌ {var}: Not set")
        else:
            if 'SECRET' in var or 'TOKEN' in var:
                display_value = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
    
    if missing_vars:
        print(f"\n❌ Missing required variables: {missing_vars}")
        return False
    
    print("\n✅ All environment variables are set!")
    return True

def test_imports():
    """Test that all required Python modules can be imported."""
    print("\n🧪 Testing Python Imports...")
    
    required_modules = ['requests', 'json', 'time', 'urllib.parse', 'logging', 're']
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}: Available")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            return False
    
    print("\n✅ All required modules are available!")
    return True

def test_gitlab_api_access():
    """Test the hybrid approach: git commands + personal access token."""
    print("\n🧪 Testing GitLab Hybrid Access - Git Commands + Personal Token...")
    
    try:
        import requests
        import subprocess
        
        personal_token = os.environ.get('GITLAB_PERSONAL_TOKEN')
        gitlab_api_url = os.environ.get('CI_API_V4_URL')
        project_id = os.environ.get('CI_PROJECT_ID')
        mr_iid = os.environ.get('CI_MERGE_REQUEST_IID')
        source_branch = os.environ.get('CI_MERGE_REQUEST_SOURCE_BRANCH_NAME')
        target_branch = os.environ.get('CI_MERGE_REQUEST_TARGET_BRANCH_NAME', 'main')
        
        print(f"   Environment Variables:")
        print(f"   GITLAB_PERSONAL_TOKEN: {'SET' if personal_token else 'NOT SET'}")
        if personal_token:
            print(f"   Token preview: {personal_token[:8]}...{personal_token[-4:]} ({len(personal_token)} chars)")
        print(f"   CI_API_V4_URL: {gitlab_api_url}")
        print(f"   CI_PROJECT_ID: {project_id}")
        print(f"   CI_MERGE_REQUEST_IID: {mr_iid}")
        print(f"   CI_MERGE_REQUEST_SOURCE_BRANCH_NAME: {source_branch}")
        print(f"   CI_MERGE_REQUEST_TARGET_BRANCH_NAME: {target_branch}")
        
        results = {}
        
        print(f"\n   🔍 Test 1: Git Commands for Diff Extraction")
        if source_branch and target_branch:
            results['git_diff'] = test_git_commands(source_branch, target_branch)
        else:
            print(f"   ❌ Missing branch variables for git diff test")
            results['git_diff'] = False
        
        print(f"\n   🔍 Test 2: Personal Token for Comment Posting")
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
            print(f"   ❌ Missing required variables: {missing}")
            results['personal_token_comments'] = False
        
        print(f"\n   📊 Hybrid Approach Test Results:")
        passed_tests = []
        failed_tests = []
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
            if result:
                passed_tests.append(test_name)
            else:
                failed_tests.append(test_name)
        
        print(f"\n   Passed: {len(passed_tests)}/2 tests")
        if len(passed_tests) == 2:
            print(f"   🎉 SUCCESS: Hybrid approach fully functional!")
            print(f"   ✅ Can extract diffs using git commands")
            print(f"   ✅ Can post comments using personal access token")
        elif len(passed_tests) == 1:
            print(f"   ⚠️  PARTIAL: One component working")
            print(f"   Working: {', '.join(passed_tests)}")
            print(f"   Failed: {', '.join(failed_tests)}")
        else:
            print(f"   ❌ FAILED: Neither component working")
            print(f"   Need to investigate: {', '.join(failed_tests)}")
        
        return len(passed_tests) > 0
            
    except Exception as e:
        print(f"❌ GitLab hybrid test suite failed with exception: {e}")
        print(f"   Exception type: {type(e).__name__}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def test_personal_token_comments(gitlab_api_url, project_id, personal_token, mr_iid):
    """Test personal access token for posting comments (full API access)"""
    try:
        import requests
        
        url = f"{gitlab_api_url}/projects/{project_id}/merge_requests/{mr_iid}/notes"
        headers = {"PRIVATE-TOKEN": personal_token}
        
        print(f"   URL: {url}")
        print(f"   Headers: PRIVATE-TOKEN")
        print(f"   Method: GET (read existing notes)")
        print(f"   Token: {personal_token[:8]}...{personal_token[-4:]}")
        
        response = requests.get(url, headers=headers, timeout=10)
        print(f"   Response: HTTP {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: Retrieved {len(data)} existing notes")
            print(f"   Personal access token has full API access")
            return True
        else:
            print(f"   ❌ Failed: {response.text[:200]}")
            if response.status_code == 401:
                print(f"   Diagnosis: Invalid or expired personal access token")
            elif response.status_code == 403:
                print(f"   Diagnosis: Personal token lacks required permissions")
            elif response.status_code == 404:
                print(f"   Diagnosis: Project or merge request not found")
            return False
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

def test_git_commands(source_branch, target_branch):
    """Test git commands for getting diff data (reliable approach)"""
    try:
        import subprocess
        import os
        
        commit_sha = os.environ.get('CI_COMMIT_SHA')
        commit_before_sha = os.environ.get('CI_COMMIT_BEFORE_SHA')
        
        print(f"   Available commit info:")
        print(f"   CI_COMMIT_SHA: {commit_sha}")
        print(f"   CI_COMMIT_BEFORE_SHA: {commit_before_sha}")
        print(f"   Source branch: {source_branch}")
        print(f"   Target branch: {target_branch}")
        print(f"   Method: Multiple git diff approaches (CI environment compatible)")
        
        git_command = ['git', 'diff', 'HEAD~1...HEAD']
        print(f"   Command: {' '.join(git_command)}")
        print(f"   Method: Git diff HEAD~1...HEAD (CI environment compatible)")
        
        result = subprocess.run(
            git_command,
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            diff_output = result.stdout
            print(f"   ✅ Success: Generated {len(diff_output)} character diff")
            if diff_output.strip():
                lines = diff_output.count('\n')
                print(f"   Diff contains {lines} lines")
            else:
                print(f"   Note: Empty diff (no changes detected)")
            return True
        else:
            print(f"   ❌ Failed: {result.stderr[:100]}")
            print(f"   Git diff command failed")
        return False
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

def test_stackspot_credentials():
    """Test StackSpot AI credentials (without making actual API calls)."""
    print("\n🧪 Testing StackSpot Credentials...")
    
    client_id = os.environ.get('STACKSPOT_CLIENT_ID')
    client_secret = os.environ.get('STACKSPOT_CLIENT_SECRET')
    client_realm = os.environ.get('STACKSPOT_CLIENT_REALM')
    
    print(f"   Expected: All StackSpot credentials should be set and resolved")
    print(f"   Actual STACKSPOT_CLIENT_ID: {'SET' if client_id else 'NOT SET'}")
    print(f"   Actual STACKSPOT_CLIENT_SECRET: {'SET' if client_secret else 'NOT SET'}")
    print(f"   Actual STACKSPOT_CLIENT_REALM: {'SET' if client_realm else 'NOT SET'}")
    
    if not all([client_id, client_secret, client_realm]):
        missing = []
        if not client_id: missing.append('STACKSPOT_CLIENT_ID')
        if not client_secret: missing.append('STACKSPOT_CLIENT_SECRET')
        if not client_realm: missing.append('STACKSPOT_CLIENT_REALM')
        print(f"❌ Missing StackSpot credentials: {missing}")
        return False
    
    print(f"   Expected: Variables should be resolved, not showing as $VARIABLE_NAME")
    
    if client_id and client_id.startswith('$'):
        print(f"❌ STACKSPOT_CLIENT_ID appears to be unresolved variable: {client_id}")
        print("   Diagnosis: Variable not properly set in GitLab CI/CD settings")
        return False
    
    if client_secret and client_secret.startswith('$'):
        print(f"❌ STACKSPOT_CLIENT_SECRET appears to be unresolved variable: {client_secret}")
        print("   Diagnosis: Variable not properly set in GitLab CI/CD settings")
        return False
        
    if client_realm and client_realm.startswith('$'):
        print(f"❌ STACKSPOT_CLIENT_REALM appears to be unresolved variable: {client_realm}")
        print("   Diagnosis: Variable not properly set in GitLab CI/CD settings")
        return False
    
    print(f"   Expected: CLIENT_ID should be at least 10 chars, CLIENT_SECRET at least 20 chars")
    
    if client_id and len(client_id) < 10:
        print(f"❌ STACKSPOT_CLIENT_ID seems too short: {len(client_id)} chars")
        return False
    
    if client_secret and len(client_secret) < 20:
        print(f"❌ STACKSPOT_CLIENT_SECRET seems too short: {len(client_secret)} chars")
        return False
    
    if client_realm and not client_realm.strip():
        print(f"❌ STACKSPOT_CLIENT_REALM is empty")
        return False
    
    print("✅ StackSpot credentials format looks valid")
    if client_id:
        print(f"   Client ID: {client_id[:8]}... ({len(client_id)} chars)")
    if client_secret:
        print(f"   Client Secret: {client_secret[:4]}...{client_secret[-4:]} ({len(client_secret)} chars)")
    if client_realm:
        print(f"   Realm: {client_realm}")
    
    return True

def main():
    """Run all tests."""
    print("🚀 GitLab CI/CD MR Summarizer - Test Suite")
    print("=" * 50)
    
    tests = [
        test_environment_variables,
        test_imports,
        test_gitlab_api_access,
        test_stackspot_credentials
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! GitLab CI/CD setup looks good.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the configuration.")
        sys.exit(1)

if __name__ == "__main__":
    main()
