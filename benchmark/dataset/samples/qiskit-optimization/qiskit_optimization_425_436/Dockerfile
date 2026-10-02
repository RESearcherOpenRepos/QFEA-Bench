ARG BASE_IMAGE=benchmark-base:qiskit_optimization_425_436
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_optimization_425_436
ENV REPOSITORY=qiskit-community/qiskit-optimization
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-optimization.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-optimization/issues/425
ENV PR_URL=https://github.com/qiskit-community/qiskit-optimization/pull/436
ENV BASE_COMMIT=3fba471f6c3113c0db60106a49d2ae61903974e9
ENV PATCHED_COMMIT=a752fd9e6af400a427a841952aac9555e454bc30
ENV PR_HEAD_COMMIT=a752fd9e6af400a427a841952aac9555e454bc30
ENV FAIL_PASS_TEST_PATHS="test/algorithms/test_grover_optimizer.py::TestGroverOptimizer::test_qubo_gas_int_zero_3_sampler test/algorithms/test_min_eigen_optimizer.py::TestMinEigenOptimizer::test_samples_qaoa"
ENV PASS_PASS_TEST_PATHS="test/algorithms/test_min_eigen_optimizer.py::TestMinEigenOptimizer::test_converter_list test/algorithms/test_min_eigen_optimizer.py::TestMinEigenOptimizer::test_samples_numpy_eigen_solver"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
