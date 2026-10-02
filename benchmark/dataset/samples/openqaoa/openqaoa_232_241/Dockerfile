# Initial recipe only; exact selectors must be supplied after pytest collection.
FROM benchmark-base:openqaoa_232_241
ENV SAMPLE_ID=openqaoa_232_241 REPOSITORY=entropicalabs/openqaoa REPOSITORY_URL=https://github.com/entropicalabs/openqaoa.git
ENV BASE_COMMIT=cf30131c4d7927e86daf6104399ee612cd6f78ec PATCHED_COMMIT=137d3f0a10391adce5bb23cf7536f2d221defb79 GIT_NO_LAZY_FETCH=1
ENV ISSUE_URL=https://github.com/entropicalabs/openqaoa/issues/232 PR_URL=https://github.com/entropicalabs/openqaoa/pull/241
COPY run.sh evaluator.py test_plan.json /benchmark/
COPY sample.json /benchmark/sample.json
ENTRYPOINT ["bash", "/benchmark/run.sh"]
