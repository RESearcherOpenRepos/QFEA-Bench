ARG BASE_IMAGE=benchmark-base:qiskit_machine_learning_385_404
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_machine_learning_385_404
ENV REPOSITORY=qiskit-community/qiskit-machine-learning
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-machine-learning.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-machine-learning/issues/385
ENV PR_URL=https://github.com/qiskit-community/qiskit-machine-learning/pull/404
ENV BASE_COMMIT=e9978f56cf978c5d4a19b1941e584f91586f804a
ENV PATCHED_COMMIT=3bf98b67618885bd09f4abbff7e381537a646fac
ENV PR_HEAD_COMMIT=f51fb6f74e1c9e3e44aa4e155b059367435f8550
ENV FAIL_PASS_TEST_PATHS="test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_classifier_with_circuit_qnn_17__None___absolute_error____statevector___True_ test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_classifier_with_opflow_qnn_17__None___absolute_error____statevector___True_ test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_untrained test/algorithms/regressors/test_neural_network_regressor.py::TestNeuralNetworkRegressor::test_regressor_with_opflow_qnn_5__None___statevector___False_ test/algorithms/regressors/test_neural_network_regressor.py::TestNeuralNetworkRegressor::test_untrained"
ENV PASS_PASS_TEST_PATHS="test/algorithms/classifiers/test_qsvc.py::TestQSVC::test_qsvc test/algorithms/regressors/test_qsvr.py::TestQSVR::test_qsvr test/algorithms/classifiers/test_vqc.py::TestVQC::test_VQC_05___statevector___2___zz_feature_map____real_amplitudes___None___binary__ test/algorithms/regressors/test_vqr.py::TestVQR::test_vqr_09__None___statevector___True_"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
