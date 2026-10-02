ARG BASE_IMAGE=benchmark-base:qiskit_nature_571_632
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_571_632
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/571
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/632
ENV BASE_COMMIT=dfeeab6cf4983ecf7718d309f30b97fdad0fa8f5
ENV PATCHED_COMMIT=68fa5fbd45bb950b5693aca0933a8369fe6f4934
ENV PR_HEAD_COMMIT=68fa5fbd45bb950b5693aca0933a8369fe6f4934
ENV FAIL_PASS_TEST_PATHS="test/algorithms/initial_points/test_hf_initial_point.py::TestHFInitialPoint::test_missing_ansatz test/algorithms/initial_points/test_hf_initial_point.py::TestHFInitialPoint::test_compute test/algorithms/ground_state_solvers/minimum_eigensolver_factories/test_vqe_ucc_factory.py::TestVQEUCCFactory::test_setters_getters test/algorithms/ground_state_solvers/test_groundstate_eigensolver.py::TestGroundStateEigensolver::test_default_initial_point"
ENV PASS_PASS_TEST_PATHS="test/algorithms/ground_state_solvers/test_groundstate_eigensolver.py::TestGroundStateEigensolver::test_vqe_uccsd test/algorithms/ground_state_solvers/test_groundstate_eigensolver.py::TestGroundStateEigensolver::test_vqe_ucc_custom test/algorithms/ground_state_solvers/test_groundstate_eigensolver.py::TestGroundStateEigensolver::test_vqe_uccsd_with_callback test/algorithms/ground_state_solvers/test_groundstate_eigensolver.py::TestGroundStateEigensolver::test_aux_ops_reusability test/algorithms/ground_state_solvers/test_groundstate_eigensolver.py::TestGroundStateEigensolver::test_eval_op_single"
ENV FAIL_PASS_EXTRA_FILES="test/algorithms/initial_points/__init__.py test/algorithms/initial_points/test_hf_initial_point.py"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
