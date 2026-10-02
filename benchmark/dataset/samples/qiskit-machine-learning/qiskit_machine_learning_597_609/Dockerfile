ARG BASE_IMAGE=benchmark-base:qiskit_machine_learning_597_609
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_machine_learning_597_609
ENV REPOSITORY=qiskit-community/qiskit-machine-learning
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-machine-learning.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-machine-learning/issues/597
ENV PR_URL=https://github.com/qiskit-community/qiskit-machine-learning/pull/609
ENV BASE_COMMIT=410d212df67f60d6d8eff88e0109bb01de03d9a8
ENV PATCHED_COMMIT=10aa219e627f62b8df59d83eceb59fbdc81c8b45
ENV PR_HEAD_COMMIT=5596444fb0592e23734a9cc2b08b9659aac55e52
ENV FAIL_PASS_TEST_PATHS="test/neural_networks/test_estimator_qnn.py::TestEstimatorQNN::test_qnn_qc_circui_construction test/neural_networks/test_sampler_qnn.py::TestSamplerQNN::test_qnn_qc_circui_construction"
ENV PASS_PASS_TEST_PATHS="test/neural_networks/test_estimator_qnn.py::TestEstimatorQNN::test_estimator_qnn_2_1 test/neural_networks/test_estimator_qnn.py::TestEstimatorQNN::test_setters_getters test/neural_networks/test_sampler_qnn.py::TestSamplerQNN::test_no_parameters test/neural_networks/test_sampler_qnn.py::TestSamplerQNN::test_setters_getters"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
