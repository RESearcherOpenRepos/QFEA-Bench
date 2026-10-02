# Initial recipe only; exact selectors must be supplied after pytest collection.
FROM benchmark-base:squlearn_62_99
ENV SAMPLE_ID=squlearn_62_99 REPOSITORY=sQUlearn/squlearn REPOSITORY_URL=https://github.com/sQUlearn/squlearn.git
ENV BASE_COMMIT=a744a781ef9720cc817b8eecfae778495d5064e1 PATCHED_COMMIT=6a41d14c9668fcf736b791ce216e26abc11e8b07 GIT_NO_LAZY_FETCH=1
ENV ISSUE_URL=https://github.com/sQUlearn/squlearn/issues/62 PR_URL=https://github.com/sQUlearn/squlearn/pull/99
COPY run.sh evaluator.py test_plan.json /benchmark/
COPY sample.json /benchmark/sample.json
ENTRYPOINT ["bash", "/benchmark/run.sh"]
