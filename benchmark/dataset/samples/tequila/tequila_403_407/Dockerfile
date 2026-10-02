# Initial recipe only; exact selectors must be supplied after pytest collection.
FROM benchmark-base:tequila_403_407
ENV SAMPLE_ID=tequila_403_407 REPOSITORY=tequilahub/tequila REPOSITORY_URL=https://github.com/tequilahub/tequila.git
ENV BASE_COMMIT=2d0f1b862d842ab83bea3c53c676a1b9bbea999c PATCHED_COMMIT=1406d26db32f7f5f0152adc246f6ded1ec3fb077 GIT_NO_LAZY_FETCH=1
ENV ISSUE_URL=https://github.com/tequilahub/tequila/issues/403 PR_URL=https://github.com/tequilahub/tequila/pull/407
COPY run.sh evaluator.py test_plan.json /benchmark/
COPY sample.json /benchmark/sample.json
ENTRYPOINT ["bash", "/benchmark/run.sh"]
