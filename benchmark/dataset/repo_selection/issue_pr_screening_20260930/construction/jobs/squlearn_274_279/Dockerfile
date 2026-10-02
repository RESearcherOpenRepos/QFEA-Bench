# Initial recipe only; exact selectors must be supplied after pytest collection.
FROM benchmark-base:squlearn_274_279
ENV SAMPLE_ID=squlearn_274_279 REPOSITORY=sQUlearn/squlearn REPOSITORY_URL=https://github.com/sQUlearn/squlearn.git
ENV BASE_COMMIT=0127e85477854bdc87e1dc3fd0b7f1f6ff3c2026 PATCHED_COMMIT=7b6c981d2a08db5a0f3cbde627d6b3410616245e GIT_NO_LAZY_FETCH=1
ENV ISSUE_URL=https://github.com/sQUlearn/squlearn/issues/274 PR_URL=https://github.com/sQUlearn/squlearn/pull/279
COPY run.sh evaluator.py test_plan.json /benchmark/
COPY sample.json /benchmark/sample.json
ENTRYPOINT ["bash", "/benchmark/run.sh"]
