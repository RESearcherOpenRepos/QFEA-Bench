ARG BASE_IMAGE=benchmark-base:qiskit_optimization_473_487
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_optimization_473_487
ENV REPOSITORY=qiskit-community/qiskit-optimization
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-optimization.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-optimization/issues/473
ENV PR_URL=https://github.com/qiskit-community/qiskit-optimization/pull/487
ENV BASE_COMMIT=b6d004115abb1f86f06b5aef2d6b12d18db60350
ENV PATCHED_COMMIT=d7b9ddba474be0a1e9abdc72f4fa68d52cd1d82f
ENV PR_HEAD_COMMIT=208daad03b9d37341694eecfe26f182e90ef703b
ENV FAIL_PASS_TEST_PATHS="test/algorithms/qrao/test_quantum_random_access_encoding.py::TestQuantumRandomAccessEncoding::test_11p_qrac_encoding test/algorithms/qrao/test_quantum_random_access_encoding.py::TestQuantumRandomAccessEncoding::test_qrac_unsupported_encoding test/algorithms/qrao/test_quantum_random_access_encoding.py::TestEncodingCommutationVerifier::test_encoding_commutation_verifier test/algorithms/qrao/test_magic_rounding.py::TestMagicRounding::test_magic_rounding_constructor test/algorithms/qrao/test_magic_rounding.py::TestMagicRounding::test_magic_rounding_round_uniform_1_1_qrac test/algorithms/qrao/test_quantum_random_access_optimizer.py::TestQuantumRandomAccessOptimizer::test_solve_numpy test/algorithms/qrao/test_quantum_random_access_optimizer.py::TestQuantumRandomAccessOptimizer::test_solve_relaxed_numpy test/algorithms/qrao/test_semideterministic_rounding.py::TestSemideterministicRounding::test_semideterministic_rounding"
ENV PASS_PASS_TEST_PATHS="test/algorithms/test_min_eigen_optimizer.py::TestMinEigenOptimizer::test_converter_list test/algorithms/test_optimization_result.py::TestOptimizationResult::test_init test/algorithms/test_optimization_result.py::TestOptimizationResult::test_prettyprint test/algorithms/test_optimization_result.py::TestOptimizationResult::test_str_repr test/applications/test_knapsack.py::TestKnapsack::test_interpret test/applications/test_knapsack.py::TestKnapsack::test_to_quadratic_program test/applications/test_max_cut.py::TestMaxcut::test_interpret test/applications/test_max_cut.py::TestMaxcut::test_to_quadratic_program test/converters/test_converters.py::TestConverters::test_binary_to_integer test/converters/test_converters.py::TestConverters::test_inequality_binary test/converters/test_converters.py::TestConverters::test_penalize_binary"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
