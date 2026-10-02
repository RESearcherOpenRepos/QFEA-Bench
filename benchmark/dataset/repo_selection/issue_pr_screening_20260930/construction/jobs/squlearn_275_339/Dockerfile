# Initial recipe only; exact selectors must be supplied after pytest collection.
FROM benchmark-base:squlearn_275_339
ENV SAMPLE_ID=squlearn_275_339 REPOSITORY=sQUlearn/squlearn REPOSITORY_URL=https://github.com/sQUlearn/squlearn.git
ENV BASE_COMMIT=3672c9e97cac7307ebaed16a5cfdd15aa836f5d2 PATCHED_COMMIT=e52584adc105f8fa211a135cd8343218f7ea4377 GIT_NO_LAZY_FETCH=1
ENV ISSUE_URL=https://github.com/sQUlearn/squlearn/issues/275 PR_URL=https://github.com/sQUlearn/squlearn/pull/339
COPY run.sh evaluator.py test_plan.json /benchmark/
COPY sample.json /benchmark/sample.json
ENTRYPOINT ["bash", "/benchmark/run.sh"]
