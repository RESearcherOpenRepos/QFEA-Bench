# Initial recipe only; exact selectors must be supplied after pytest collection.
FROM benchmark-base:openqaoa_112_85
ENV SAMPLE_ID=openqaoa_112_85 REPOSITORY=entropicalabs/openqaoa REPOSITORY_URL=https://github.com/entropicalabs/openqaoa.git
ENV BASE_COMMIT=a463e69e2e3dbd8c877932d759a4dfd1c7469246 PATCHED_COMMIT=b1463b99b5ed4441dbc328fab357dbe1cef31db4 GIT_NO_LAZY_FETCH=1
ENV ISSUE_URL=https://github.com/entropicalabs/openqaoa/issues/112 PR_URL=https://github.com/entropicalabs/openqaoa/pull/85
COPY run.sh evaluator.py test_plan.json /benchmark/
COPY sample.json /benchmark/sample.json
ENTRYPOINT ["bash", "/benchmark/run.sh"]
