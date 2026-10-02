ARG BASE_IMAGE=benchmark-base:qiskit_machine_learning_326_360
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_machine_learning_326_360
ENV REPOSITORY=qiskit-community/qiskit-machine-learning
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-machine-learning.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-machine-learning/issues/326
ENV PR_URL=https://github.com/qiskit-community/qiskit-machine-learning/pull/360
ENV BASE_COMMIT=fd8e4e0933d33d88a833091b7cb187246ca8d792
ENV PATCHED_COMMIT=c81306a30435cdc5ab511552aba85b569f17d2a5
ENV PR_HEAD_COMMIT=4f88c3e4866a62964b8a7108d814a863415e64aa
ENV FAIL_PASS_TEST_PATHS="test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_save_load_1_opflow test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_save_load_2_circuit_qnn test/algorithms/classifiers/test_pegasos_qsvc.py::TestPegasosQSVC::test_save_load test/algorithms/classifiers/test_qsvc.py::TestQSVC::test_save_load test/algorithms/regressors/test_neural_network_regressor.py::TestNeuralNetworkRegressor::test_save_load test/algorithms/regressors/test_qsvr.py::TestQSVR::test_save_load"
ENV PASS_PASS_TEST_PATHS="test/algorithms/classifiers/test_qsvc.py::TestQSVC::test_qsvc test/algorithms/classifiers/test_pegasos_qsvc.py::TestPegasosQSVC::test_qsvc test/algorithms/regressors/test_qsvr.py::TestQSVR::test_qsvr"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
