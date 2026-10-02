ARG BASE_IMAGE=benchmark-base:qiskit_optimization_8_18
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_optimization_8_18
ENV REPOSITORY=qiskit-community/qiskit-optimization
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-optimization.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-optimization/issues/8
ENV PR_URL=https://github.com/qiskit-community/qiskit-optimization/pull/18
ENV BASE_COMMIT=6fba541812d6c37943f418c4b522542d442888bb
ENV PATCHED_COMMIT=fb58e1c9da67bcb3fa81ee68422acb2daebf5abd
ENV PR_HEAD_COMMIT=a528041803989328d178f522040da3c78058bed2
ENV FAIL_PASS_TEST_PATHS="test/test_warm_start_qaoa.py::TestWarmStartQAOAOptimizer::test_max_cut test/test_warm_start_qaoa.py::TestWarmStartQAOAOptimizer::test_constrained_binary test/test_warm_start_qaoa.py::TestWarmStartQAOAOptimizer::test_simple_qubo"
ENV PASS_PASS_TEST_PATHS="test/test_min_eigen_optimizer.py::TestMinEigenOptimizer::test_converter_list test/test_min_eigen_optimizer.py::TestMinEigenOptimizer::test_samples test/test_slsqp.py::TestSlsqpOptimizer::test_slsqp_optimizer"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
