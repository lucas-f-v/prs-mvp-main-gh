# GitLab CI/CD MR Summarizer

🤖 **Automated AI-powered merge request summaries using StackSpot AI and GitLab CI/CD**

This project provides a **zero-infrastructure** solution for automatically generating AI summaries of GitLab merge requests using StackSpot AI, running entirely within GitLab's CI/CD pipeline.

## Table of Contents
- [Features](#features)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Advanced Setup](#advanced-setup)
- [Comparison with AWS Version](#comparison-with-aws-version)
- [Diff Filtering](#diff-filtering)
- [Troubleshooting](#troubleshooting)
- [Monitoring and Performance](#monitoring-and-performance)
- [Requirements](#requirements)
- [Support](#support)
- [Success](#success)

## ✨ Features

- ✅ **Zero Infrastructure** - No AWS services or external hosting required
- ✅ **Native GitLab Integration** - Uses GitLab CI/CD and built-in variables
- ✅ **Hybrid Approach** - Git commands + Personal Access Token for GitLab.com Free tier compatibility
- ✅ **Automatic Scaling** - GitLab handles concurrency and resource management
- ✅ **Error Handling** - Graceful failure with informative error comments
- ✅ **Large Diff Support** - Intelligent chunking and simplification for large changes
- ✅ **Retry Logic** - Automatic retries for transient failures
- ✅ **Duplicate Code Reports** - jscpd compares base and merged code and posts MR comments

## 🚀 Quick Start

### 1. Copy Files
```bash
# Copy to your GitLab repository
cp .gitlab-ci.yml /path/to/your/repo/
cp -r scripts/ /path/to/your/repo/
```

### 2. Create Personal Access Token
1. Go to GitLab.com → **User Settings → Access Tokens**
2. Create new token with:
   - **Name**: `CI-Pipeline-Personal-Token`
   - **Scopes**: `api` (full API access)
   - **Expiration**: 1 year from now
3. Copy the generated token

### 3. Configure CI/CD Variables
Go to your project **Settings → CI/CD → Variables** and add:

| Variable | Value | Protected | Masked |
|----------|-------|-----------|--------|
| `GITLAB_PERSONAL_TOKEN` | Your personal access token | ✅ | ✅ |
| `STACKSPOT_CLIENT_ID` | Your StackSpot client ID | ✅ | ❌ |
| `STACKSPOT_CLIENT_SECRET` | Your StackSpot client secret | ✅ | ✅ |
| `STACKSPOT_CLIENT_REALM` | Your StackSpot realm | ✅ | ❌ |

### 4. Test
Create a merge request with code changes and watch the AI summary appear automatically!

### 5. Duplicate Code Report (optional)
A `jscpd` job compares duplicate lines between the target branch and the merge
result. It runs in the `code_quality` stage and posts a Markdown table of any
duplicated blocks to the merge request:

```markdown
| Lines | First File | Second File |
|---|---|---|
| 12 | src/app.py:10-21 | src/utils/helpers.py:42-53 |
```

To try it locally:

```bash
./scripts/run-jscpd-merge.sh
CI_API_V4_URL=https://gitlab.com/api/v4 \
CI_PROJECT_ID=123 \
CI_MERGE_REQUEST_IID=1 \
GITLAB_PERSONAL_TOKEN=your-token \
./scripts/post-jscpd-merge-comment.sh
```

The scripts generate `jscpd-base.json` and `jscpd-merged.json` and clean up
their temporary worktrees. The JSON files are ignored by git.

## 🔧 How It Works

### Hybrid Architecture
This implementation uses a **hybrid approach** optimized for GitLab.com Free tier:

```
GitLab MR Event → CI/CD Pipeline → Git Commands (diff) → StackSpot AI → Personal Token (comment)
```

1. **Trigger**: Pipeline runs automatically on MR creation/updates
2. **Diff Extraction**: Uses `git diff HEAD~1...HEAD` (reliable, no API limitations)
3. **AI Processing**: Sends diff to StackSpot AI for intelligent summarization
4. **Comment Posting**: Posts summary using personal access token (full API access)

### GitLab Built-in Variables Used
The script automatically uses these GitLab-provided variables:

- `CI_PROJECT_ID` - GitLab project ID
- `CI_MERGE_REQUEST_IID` - MR internal ID
- `CI_MERGE_REQUEST_SOURCE_BRANCH_NAME` - Source branch for git diff
- `CI_MERGE_REQUEST_TARGET_BRANCH_NAME` - Target branch for git diff
- `CI_API_V4_URL` - GitLab API v4 URL
- `CI_PIPELINE_SOURCE` - Pipeline trigger source

### CI Environment Setup
The pipeline automatically:
- Installs git in `python:3.12-slim` containers
- Configures git for CI environment
- Handles authentication and error scenarios

## 📁 Project Structure

```
├── .gitlab-ci.yml                    # CI/CD pipeline configuration
├── scripts/
│   ├── gitlab_ci_summarizer.py       # Main summarizer script
│   ├── post-jscpd-merge-comment.sh   # Post duplicate code table to MR
│   ├── run-jscpd-merge.sh            # Generate jscpd reports for base/merged code
│   └── test_gitlab_ci.py             # Configuration test script
└── README.md                         # This file
```

## 🔧 Advanced Setup

### StackSpot AI Credentials

To get your StackSpot AI credentials:

1. Log in to your StackSpot AI account
2. Go to API settings or developer console
3. Create or find your API credentials:
   - **Client ID**: Usually starts with `stk_`
   - **Client Secret**: Long random string
   - **Realm**: Your organization realm (e.g., `your-company`)

### Security Configuration

**Important Security Notes:**
- ✅ **Always mark secrets as "Protected"** (only available on protected branches)
- ✅ **Mark sensitive values as "Masked"** (hidden in job logs)
- ✅ **Use "Variable" type** (not "File" type)

### Pipeline Behavior

The pipeline will:
- ✅ **Trigger automatically** on MR creation/updates
- ✅ **Run tests first** to validate configuration
- ✅ **Generate AI summary** using StackSpot AI
- ✅ **Post comment** with summary to the MR
- ✅ **Allow MR to proceed** even if summary fails

## 🎯 Customization Options

### Modify RQC Slugs

Edit `scripts/gitlab_ci_summarizer.py`:

```python
# Change these to match your StackSpot RQCs
RQC_PARTIAL_SUMMARY_SLUG = "your-partial-summary-rqc"
RQC_TOTAL_SUMMARY_SLUG = "your-total-summary-rqc"
```

### Adjust Pipeline Rules

Edit `.gitlab-ci.yml` to change when the pipeline runs:

```yaml
# Example: Only run on specific branches
rules:
  - if: $CI_PIPELINE_SOURCE == "merge_request_event" && $CI_MERGE_REQUEST_TARGET_BRANCH_NAME == "main"
    when: always
```

### Change Timeout Settings

```yaml
# Increase timeout for large MRs
timeout: 30m
```

### Add File Filters

```yaml
# Only run on code changes
rules:
  - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    changes:
      - "**/*.py"
      - "**/*.js"
      - "**/*.ts"
    when: always
```

## 🆚 Comparison with AWS Version

| Feature | AWS Version | GitLab CI/CD Version |
|---------|-------------|---------------------|
| **Infrastructure** | 8+ AWS services | 0 services |
| **Code Complexity** | 2000+ lines | ~400 lines |
| **Monthly Cost** | $50-200 | $0-5 |
| **Deployment** | Terraform + ECS | Git push |
| **Latency** | ~1-2 seconds | < 1 second |
| **Maintenance** | High | Zero |

## 🧹 Diff Filtering

Fine‑tune which files are sent to StackSpot AI by adding a `diff_filter.json`
file to your repository root. It uses simple allow/deny arrays of glob patterns:

```json
{
  "allow": ["src/**", "docs/**"],
  "deny": ["src/vendor/**", "*.md"]
}
```

If the `allow` list is empty, every file is considered allowed unless a `deny`
rule matches. When `allow` contains patterns, a path must match at least one of
them and must not match any `deny` pattern. Deny rules always win when both
match.

When the pipeline runs it generates `diff-filter-report.json` showing which
files were included or filtered out based on these rules.

## 🔍 Troubleshooting

### Common Issues

**Pipeline doesn't trigger**
- Check `.gitlab-ci.yml` is in repository root
- Verify CI/CD is enabled in project settings
- Check pipeline rules match your MR conditions

**Missing environment variables**
- Verify all CI/CD variables are set correctly
- Check variable names match exactly (case-sensitive)
- Ensure variables are not expired

**Git command not found**
- Ensure `.gitlab-ci.yml` includes git installation in `before_script`
- Check job logs for git installation errors

**API access denied**
- Verify `GITLAB_PERSONAL_TOKEN` has `api` scope
- Check token is not expired or revoked

**StackSpot AI authentication failed**
- Verify StackSpot credentials are correct
- Check that your StackSpot account is active
- Ensure the realm name is correct

### Advanced Troubleshooting

**Large MR processing fails**
- The script automatically chunks large diffs
- Increase job timeout in `.gitlab-ci.yml`
- Consider using more powerful GitLab runners

**Debug Mode**
Enable debug logging by adding to `.gitlab-ci.yml`:

```yaml
variables:
  CI_DEBUG_TRACE: "true"  # Enable detailed job logs
```

**Manual Testing**
Test the script locally (requires GitLab environment variables):

```bash
# Set test environment variables
export CI_PROJECT_ID="12345"
export CI_MERGE_REQUEST_IID="1"
export CI_MERGE_REQUEST_SOURCE_BRANCH_NAME="feature-branch"
export CI_MERGE_REQUEST_TARGET_BRANCH_NAME="main"
export GITLAB_PERSONAL_TOKEN="your-personal-token"
export CI_API_V4_URL="https://gitlab.com/api/v4"
export STACKSPOT_CLIENT_ID="your-client-id"
export STACKSPOT_CLIENT_SECRET="your-client-secret"
export STACKSPOT_CLIENT_REALM="your-realm"

# Run the script
python scripts/gitlab_ci_summarizer.py
```

## 📊 Monitoring and Performance

### Pipeline Success Rate
Monitor in **CI/CD > Analytics**:
- Pipeline success rate
- Job duration trends
- Failure patterns

### Cost Monitoring
Track CI/CD minutes usage:
- Go to **Settings > Usage Quotas**
- Monitor CI/CD minutes consumption
- Set up alerts for quota limits

### Performance Optimization
- **Caching**: Add caching for Python dependencies
- **Parallel Jobs**: Split large MRs across multiple jobs
- **Resource Limits**: Adjust memory/CPU limits for runners

## 🎯 Requirements

- GitLab project with CI/CD enabled
- StackSpot AI account with API credentials
- Personal Access Token with `api` scope
- GitLab Runner (GitLab.com provides shared runners)

## 🤝 Support

### Getting Help

1. **Check job logs** in GitLab CI/CD interface
2. **Review this guide** for common solutions
3. **Test configuration** using the test script
4. **Check StackSpot AI status** and documentation

### Useful Commands

```bash
# View recent pipelines
curl -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/$PROJECT_ID/pipelines"

# View job logs
curl -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/$PROJECT_ID/jobs/$JOB_ID/trace"
```

## 🎉 Success!

Once setup is complete, you should see:
- ✅ Automatic pipeline triggers on MR events
- ✅ AI-generated summaries posted as MR comments
- ✅ Reliable processing of code changes
- ✅ Zero infrastructure maintenance required

The GitLab CI/CD version provides the same AI-powered summaries as the AWS version with dramatically reduced complexity and cost!
