ARG BASE_IMAGE=benchmark-base:qiskit_machine_learning_387_398
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_machine_learning_387_398
ENV REPOSITORY=qiskit-community/qiskit-machine-learning
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-machine-learning.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-machine-learning/issues/387
ENV PR_URL=https://github.com/qiskit-community/qiskit-machine-learning/pull/398
ENV BASE_COMMIT=005c9dc0cfb3068850fb33a709faa4bbd30b7c80
ENV PATCHED_COMMIT=5df0a738d1120c492ce7fb5e18d61ee8489a6b78
ENV PR_HEAD_COMMIT=5df0a738d1120c492ce7fb5e18d61ee8489a6b78
ENV FAIL_PASS_TEST_PATHS="test/algorithms/classifiers/test_pegasos_qsvc.py::TestPegasosQSVC::test_decision_function"
ENV PASS_PASS_TEST_PATHS="test/algorithms/classifiers/test_pegasos_qsvc.py::TestPegasosQSVC::test_qsvc test/algorithms/classifiers/test_pegasos_qsvc.py::TestPegasosQSVC::test_qsvc_4d test/algorithms/classifiers/test_pegasos_qsvc.py::TestPegasosQSVC::test_precomputed_kernel test/algorithms/classifiers/test_pegasos_qsvc.py::TestPegasosQSVC::test_change_kernel test/algorithms/classifiers/test_pegasos_qsvc.py::TestPegasosQSVC::test_change_kernel_types"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
