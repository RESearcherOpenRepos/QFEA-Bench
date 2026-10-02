# Initial recipe only; exact selectors must be supplied after pytest collection.
FROM benchmark-base:tequila_400_411
ENV SAMPLE_ID=tequila_400_411 REPOSITORY=tequilahub/tequila REPOSITORY_URL=https://github.com/tequilahub/tequila.git
ENV BASE_COMMIT=a257bc0f49d3fa2d8262ecffc172074ac1812fff PATCHED_COMMIT=2d0f1b862d842ab83bea3c53c676a1b9bbea999c GIT_NO_LAZY_FETCH=1
ENV ISSUE_URL=https://github.com/tequilahub/tequila/issues/400 PR_URL=https://github.com/tequilahub/tequila/pull/411
COPY run.sh evaluator.py test_plan.json /benchmark/
COPY sample.json /benchmark/sample.json
ENTRYPOINT ["bash", "/benchmark/run.sh"]
