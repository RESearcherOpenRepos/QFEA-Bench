# Initial recipe only; exact selectors must be supplied after pytest collection.
FROM benchmark-base:openqaoa_36_71
ENV SAMPLE_ID=openqaoa_36_71 REPOSITORY=entropicalabs/openqaoa REPOSITORY_URL=https://github.com/entropicalabs/openqaoa.git
ENV BASE_COMMIT=a2444b5192118b5174d315c5c18ab9ee13571501 PATCHED_COMMIT=d4b99fe091869e0e3d3beaf9365c98228c30e0bf GIT_NO_LAZY_FETCH=1
ENV ISSUE_URL=https://github.com/entropicalabs/openqaoa/issues/36 PR_URL=https://github.com/entropicalabs/openqaoa/pull/71
COPY run.sh evaluator.py test_plan.json /benchmark/
COPY sample.json /benchmark/sample.json
ENTRYPOINT ["bash", "/benchmark/run.sh"]
