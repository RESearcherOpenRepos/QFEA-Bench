# Initial recipe only; exact selectors must be supplied after pytest collection.
FROM benchmark-base:squlearn_112_154
ENV SAMPLE_ID=squlearn_112_154 REPOSITORY=sQUlearn/squlearn REPOSITORY_URL=https://github.com/sQUlearn/squlearn.git
ENV BASE_COMMIT=3bb269ebb14818b87041e61690be28a168af2833 PATCHED_COMMIT=11a90f284dcbef9e5e543b927929b2a97d113f74 GIT_NO_LAZY_FETCH=1
ENV ISSUE_URL=https://github.com/sQUlearn/squlearn/issues/112 PR_URL=https://github.com/sQUlearn/squlearn/pull/154
COPY run.sh evaluator.py test_plan.json /benchmark/
COPY sample.json /benchmark/sample.json
ENTRYPOINT ["bash", "/benchmark/run.sh"]
