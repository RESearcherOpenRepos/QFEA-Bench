# Initial recipe only; exact selectors must be supplied after pytest collection.
FROM benchmark-base:qiskit_addon_sqd_265_343
ENV SAMPLE_ID=qiskit_addon_sqd_265_343 REPOSITORY=Qiskit/qiskit-addon-sqd REPOSITORY_URL=https://github.com/Qiskit/qiskit-addon-sqd.git
ENV BASE_COMMIT=f65e80ab3a0137fba99c3dc474dd9f804d87ba1b PATCHED_COMMIT=297f65ab5bf3fd5e7a80f74106b209b6dbb7b0bb GIT_NO_LAZY_FETCH=1
ENV ISSUE_URL=https://github.com/Qiskit/qiskit-addon-sqd/issues/265 PR_URL=https://github.com/Qiskit/qiskit-addon-sqd/pull/343
COPY run.sh evaluator.py test_plan.json /benchmark/
COPY sample.json /benchmark/sample.json
ENTRYPOINT ["bash", "/benchmark/run.sh"]
