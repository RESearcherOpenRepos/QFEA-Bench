# Initial recipe only; exact selectors must be supplied after pytest collection.
FROM benchmark-base:squlearn_266_301
ENV SAMPLE_ID=squlearn_266_301 REPOSITORY=sQUlearn/squlearn REPOSITORY_URL=https://github.com/sQUlearn/squlearn.git
ENV BASE_COMMIT=e3866c7448a9d05e4ba2360fdc9b309168caa3e1 PATCHED_COMMIT=1b0adcd9d26f56ce19ae8122e8631901c5b303df GIT_NO_LAZY_FETCH=1
ENV ISSUE_URL=https://github.com/sQUlearn/squlearn/issues/266 PR_URL=https://github.com/sQUlearn/squlearn/pull/301
COPY run.sh evaluator.py test_plan.json /benchmark/
COPY sample.json /benchmark/sample.json
ENTRYPOINT ["bash", "/benchmark/run.sh"]
