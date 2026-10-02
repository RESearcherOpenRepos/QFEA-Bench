ARG BASE_IMAGE=benchmark-base:qiskit_machine_learning_401_470
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_machine_learning_401_470
ENV REPOSITORY=qiskit-community/qiskit-machine-learning
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-machine-learning.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-machine-learning/issues/401
ENV PR_URL=https://github.com/qiskit-community/qiskit-machine-learning/pull/470
ENV BASE_COMMIT=2629e70c75f59bb7315cdd012dc8ed65898ffaf9
ENV PATCHED_COMMIT=670bc12ac7b696acdf4b1ea3e9f4242953a8555d
ENV PR_HEAD_COMMIT=86b9ae2e368939fd6a891dcb35d22bf77737759c
ENV FAIL_PASS_TEST_PATHS="test/neural_networks/test_estimator_qnn.py::TestEstimatorQNN::test_default_observables test/neural_networks/test_estimator_qnn.py::TestEstimatorQNN::test_estimator_qnn_1_1 test/neural_networks/test_estimator_qnn.py::TestEstimatorQNN::test_estimator_qnn_1_2 test/neural_networks/test_estimator_qnn.py::TestEstimatorQNN::test_estimator_qnn_2_1 test/neural_networks/test_estimator_qnn.py::TestEstimatorQNN::test_estimator_qnn_2_2 test/neural_networks/test_estimator_qnn.py::TestEstimatorQNN::test_no_input_parameters test/neural_networks/test_estimator_qnn.py::TestEstimatorQNN::test_no_parameters test/neural_networks/test_estimator_qnn.py::TestEstimatorQNN::test_no_weight_parameters test/neural_networks/test_estimator_qnn.py::TestEstimatorQNN::test_setters_getters test/neural_networks/test_estimator_qnn.py::TestEstimatorQNN::test_single_observable test/algorithms/regressors/test_vqr_estimator_qnn.py::TestVQR::test_incorrect_observable test/algorithms/regressors/test_vqr_estimator_qnn.py::TestVQR::test_properties test/algorithms/regressors/test_vqr_estimator_qnn.py::TestVQR::test_vqr_5__None__True_ test/algorithms/regressors/test_vqr_estimator_qnn.py::TestVQR::test_vqr_6__None__False_ test/algorithms/regressors/test_vqr.py::TestVQR::test_incorrect_observable"
ENV PASS_PASS_TEST_PATHS="test/neural_networks/test_opflow_qnn.py::TestOpflowQNN::test_opflow_qnn_1_1_1___sv___True_ test/neural_networks/test_neural_network.py::TestNeuralNetwork::test_data_gradients test/algorithms/regressors/test_neural_network_regressor.py::TestNeuralNetworkRegressor::test_untrained test/algorithms/regressors/test_qsvr.py::TestQSVR::test_qsvr"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
