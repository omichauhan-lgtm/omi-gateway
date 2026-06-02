## Description
Provide a clear, concise summary of the proposed changes, including the design decisions and architectural motivation.

## Related Issue / Context
Fixes # (issue number) or references relevant discussion thread.

## Changes Type
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation / Artifact Update

## Verification & Testing
Describe the tests and methods used to verify your modifications.

> [!IMPORTANT]
> All code changes affecting classifier weights, routing, or calibration matrices **MUST** successfully run and pass the evaluation regression suite.

- [ ] I have executed the regression suite: `python evals/regression_suite.py` (Attach results/logs below if relevant).
- [ ] I have verified the endpoints using unit tests: `python benchmarks/reproducibility/test_public_endpoints.py`
- [ ] Manual verification details:

## Checklist
- [ ] My code follows the code style guidelines of this project.
- [ ] I have updated/appended relevant docstrings and unit tests.
- [ ] I have updated the documentation / README if introducing changes to policy matrices.
- [ ] All new and existing tests pass.
- [ ] My changes do not introduce new security vulnerabilities or leak secrets.
