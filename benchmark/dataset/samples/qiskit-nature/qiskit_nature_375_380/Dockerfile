ARG BASE_IMAGE=benchmark-base:qiskit_nature_375_380
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_375_380
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/375
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/380
ENV BASE_COMMIT=aeef5f94876c2950ce4036952e3eebbc87fe7c2a
ENV PATCHED_COMMIT=2590ee8f015a842649036cfa6cf6c76b863c8dc0
ENV PR_HEAD_COMMIT=2590ee8f015a842649036cfa6cf6c76b863c8dc0
ENV FAIL_PASS_TEST_PATHS="test/algorithms/ground_state_solvers/test_groundstate_eigensolver.py::TestGroundStateEigensolver::test_vqe_uccsd_with_callback test/algorithms/excited_state_solvers/test_bosonic_esc_calculation.py::TestBosonicESCCalculation::test_vqe_uvccsd_with_callback"
ENV PASS_PASS_TEST_PATHS="test/algorithms/ground_state_solvers/test_groundstate_eigensolver.py::TestGroundStateEigensolver::test_vqe_uccsd test/algorithms/ground_state_solvers/test_groundstate_eigensolver.py::TestGroundStateEigensolver::test_vqe_ucc_custom test/algorithms/excited_state_solvers/test_bosonic_esc_calculation.py::TestBosonicESCCalculation::test_vqe_uvccsd_factory"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
