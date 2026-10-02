ARG BASE_IMAGE=benchmark-base:qiskit_machine_learning_320_412
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_machine_learning_320_412
ENV REPOSITORY=qiskit-community/qiskit-machine-learning
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-machine-learning.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-machine-learning/issues/320
ENV PR_URL=https://github.com/qiskit-community/qiskit-machine-learning/pull/412
ENV BASE_COMMIT=3e1ed39e3f4d9b650db181866b6d12865a496613
ENV PATCHED_COMMIT=41bcc3b2af9b14dde3553b8e7acd0c8bacb7c507
ENV PR_HEAD_COMMIT=41bcc3b2af9b14dde3553b8e7acd0c8bacb7c507
ENV FAIL_PASS_TEST_PATHS="test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_categorical_data_1__True___absolute_error__ test/algorithms/classifiers/test_vqc.py::TestVQC::test_VQC_003___statevector___2___zz_feature_map____real_amplitudes____cobyla____no_one_hot__ test/algorithms/classifiers/test_vqc.py::TestVQC::test_categorical"
ENV PASS_PASS_TEST_PATHS="test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_bad_one_hot_data test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_num_classes_data_1_True test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_num_classes_data_2_False test/algorithms/classifiers/test_vqc.py::TestVQC::test_VQC_non_parameterized test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_categorical_data_2__True___squared_error__ test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_categorical_data_3__True___cross_entropy__ test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_categorical_data_4__False___absolute_error__ test/algorithms/classifiers/test_neural_network_classifier.py::TestNeuralNetworkClassifier::test_categorical_data_5__False___squared_error__"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
