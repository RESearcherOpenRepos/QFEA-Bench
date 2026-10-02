# syntax=docker/dockerfile:1.7
FROM benchmark-base:qiskit_machine_learning_63_102

ARG SAMPLE_ID=qiskit_machine_learning_63_102
ARG REPOSITORY=qiskit-community/qiskit-machine-learning
ARG REPOSITORY_URL=https://github.com/qiskit-community/qiskit-machine-learning.git
ARG ISSUE_URL=https://github.com/qiskit-community/qiskit-machine-learning/issues/63
ARG PR_URL=https://github.com/qiskit-community/qiskit-machine-learning/pull/102
ARG BASE_COMMIT=610e99bfe758b320571d08c655ae18d7b3543fc2
ARG PATCHED_COMMIT=20ee69a5df54548d04558e817d8f35b342168a28

ENV SAMPLE_ID=${SAMPLE_ID}
ENV REPOSITORY=${REPOSITORY}
ENV REPOSITORY_URL=${REPOSITORY_URL}
ENV ISSUE_URL=${ISSUE_URL}
ENV PR_URL=${PR_URL}
ENV BASE_COMMIT=${BASE_COMMIT}
ENV PATCHED_COMMIT=${PATCHED_COMMIT}
ENV DEFAULT_TARGET=patched
ENV FAIL_PASS_TEST_PATHS="test/utils/loss_functions/test_loss_functions.py::TestLossFunctions::test_l1_l2_loss_2___5_____5_____l1__ test/utils/loss_functions/test_loss_functions.py::TestLossFunctions::test_l1_l2_loss_5___5_____5_____l2__"
ENV PASS_PASS_TEST_PATHS="test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_classifier_with_opflow_qnn_1___cobyla____l1____statevector__ test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_classifier_with_opflow_qnn_3___cobyla____l2____statevector__ test/algorithms/regressors/test_neural_network_regressor.py::TestNeuralNetworkRegressor::test_regressor_with_opflow_qnn_1___cobyla____statevector__ test/algorithms/regressors/test_neural_network_regressor.py::TestNeuralNetworkRegressor::test_regressor_with_opflow_qnn_3___bfgs____statevector__"

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

WORKDIR /workspace/repo
ENTRYPOINT ["/benchmark/run.sh"]
