# Initial recipe only; exact selectors must be supplied after pytest collection.
FROM benchmark-base:tequila_406_409
ENV SAMPLE_ID=tequila_406_409 REPOSITORY=tequilahub/tequila REPOSITORY_URL=https://github.com/tequilahub/tequila.git
ENV BASE_COMMIT=beb74a6c26f80120bc049172854c5a2927124a52 PATCHED_COMMIT=5a504be7f20ee5cb80c2db6127ce1c387d1ff2c5 GIT_NO_LAZY_FETCH=1
ENV ISSUE_URL=https://github.com/tequilahub/tequila/issues/406 PR_URL=https://github.com/tequilahub/tequila/pull/409
COPY run.sh evaluator.py test_plan.json /benchmark/
COPY sample.json /benchmark/sample.json
ENTRYPOINT ["bash", "/benchmark/run.sh"]
