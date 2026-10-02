ARG BASE_IMAGE=benchmark-base:qiskit_optimization_41_114
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_optimization_41_114
ENV REPOSITORY=qiskit-community/qiskit-optimization
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-optimization.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-optimization/issues/41
ENV PR_URL=https://github.com/qiskit-community/qiskit-optimization/pull/114
ENV BASE_COMMIT=a30112512ab6a5c20f09745267587148fceaae2f
ENV PATCHED_COMMIT=969ec9293eee3abdf4ef85be9c91bee939c5212e
ENV PR_HEAD_COMMIT=969ec9293eee3abdf4ef85be9c91bee939c5212e
ENV FAIL_PASS_TEST_PATHS="test/converters/test_converters.py::TestConverters::test_maximize_to_minimize test/converters/test_converters.py::TestConverters::test_empty_problem test/algorithms/test_grover_optimizer.py::TestGroverOptimizer::test_converter_list test/algorithms/test_min_eigen_optimizer.py::TestMinEigenOptimizer::test_converter_list test/algorithms/test_min_eigen_optimizer.py::TestMinEigenOptimizer::test_samples_numpy_eigen_solver"
ENV PASS_PASS_TEST_PATHS="test/converters/test_converters.py::TestConverters::test_integer_to_binary test/converters/test_converters.py::TestConverters::test_optimizationproblem_to_ising test/converters/test_converters.py::TestConverters::test_penalize_binary test/converters/test_converters.py::TestConverters::test_penalize_sense test/algorithms/test_grover_optimizer.py::TestGroverOptimizer::test_qubo_gas_int_simple test/algorithms/test_grover_optimizer.py::TestGroverOptimizer::test_qubo_gas_int_simple_maximize test/algorithms/test_min_eigen_optimizer.py::TestMinEigenOptimizer::test_converter_list test/algorithms/test_min_eigen_optimizer.py::TestMinEigenOptimizer::test_samples_numpy_eigen_solver test/algorithms/test_warm_start_qaoa.py::TestWarmStartQAOAOptimizer::test_simple_qubo"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
