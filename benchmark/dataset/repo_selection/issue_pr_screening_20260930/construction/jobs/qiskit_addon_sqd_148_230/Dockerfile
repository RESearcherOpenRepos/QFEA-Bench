# Initial recipe only; exact selectors must be supplied after pytest collection.
FROM benchmark-base:qiskit_addon_sqd_148_230
ENV SAMPLE_ID=qiskit_addon_sqd_148_230 REPOSITORY=Qiskit/qiskit-addon-sqd REPOSITORY_URL=https://github.com/Qiskit/qiskit-addon-sqd.git
ENV BASE_COMMIT=780c30c68c877db7d4ce8f70a1ecd055a580277a PATCHED_COMMIT=0f8d2805b811fb0853f99de2756dc97893edcbb3 GIT_NO_LAZY_FETCH=1
ENV ISSUE_URL=https://github.com/Qiskit/qiskit-addon-sqd/issues/148 PR_URL=https://github.com/Qiskit/qiskit-addon-sqd/pull/230
COPY run.sh evaluator.py test_plan.json /benchmark/
COPY sample.json /benchmark/sample.json
ENTRYPOINT ["bash", "/benchmark/run.sh"]
