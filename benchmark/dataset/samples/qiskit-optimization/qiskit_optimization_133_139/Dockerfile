ARG BASE_IMAGE=benchmark-base:qiskit_optimization_133_139
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_optimization_133_139
ENV REPOSITORY=qiskit-community/qiskit-optimization
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-optimization.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-optimization/issues/133
ENV PR_URL=https://github.com/qiskit-community/qiskit-optimization/pull/139
ENV BASE_COMMIT=e7f7132d0add6787fb86266140f194284317b0cb
ENV PATCHED_COMMIT=00fd67e029ded6b76e1a9f73eb17ccc628a4f776
ENV PR_HEAD_COMMIT=cda556eda00804d1fea9194a4953995c1165cf9c
ENV FAIL_PASS_TEST_PATHS=test/algorithms/test_cplex_optimizer.py::TestCplexOptimizer::test_cplex_optimizer_no_solution_1___op_ip1_lp____0__2___6_
ENV PASS_PASS_TEST_PATHS="test/algorithms/test_cplex_optimizer.py::TestCplexOptimizer::test_cplex_optimizer_1___op_ip1_lp____0__2___6_ test/algorithms/test_cplex_optimizer.py::TestCplexOptimizer::test_cplex_optimizer_2___op_mip1_lp____1__1__0___6_ test/algorithms/test_cplex_optimizer.py::TestCplexOptimizer::test_cplex_optimizer_3___op_lp1_lp____0_25__1_75___5_875_ test/algorithms/test_cobyla_optimizer.py::TestCobylaOptimizer::test_cobyla_optimizer test/algorithms/test_slsqp.py::TestSlsqpOptimizer::test_slsqp_optimizer test/algorithms/test_slsqp.py::TestSlsqpOptimizer::test_slsqp_bounded"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
