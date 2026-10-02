ARG BASE_IMAGE=benchmark-base:qiskit_machine_learning_920_924
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_machine_learning_920_924
ENV REPOSITORY=qiskit-community/qiskit-machine-learning
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-machine-learning.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-machine-learning/issues/920
ENV PR_URL=https://github.com/qiskit-community/qiskit-machine-learning/pull/924
ENV BASE_COMMIT=ff55d2c23b7ee023d6a0ecf3094c9109ed2ddc98
ENV PATCHED_COMMIT=9725adebbffc9dfe96825038b6f894478da3d1da
ENV PR_HEAD_COMMIT=17a57355a8e267654fefc29379a1d55083ad6469
ENV FAIL_PASS_TEST_PATHS="test/optimizers/test_optimizers.py::TestOptimizers::test_nlopt_7"
ENV PASS_PASS_TEST_PATHS="test/optimizers/test_optimizers.py::TestOptimizers::test_nlopt_2 test/optimizers/test_optimizers.py::TestOptimizers::test_nlopt_3 test/optimizers/test_optimizers.py::TestOptimizers::test_nlopt_5 test/optimizers/test_optimizers.py::TestOptimizers::test_nlopt_6"
ENV DEFAULT_TARGET=patched

RUN python -m pip install --force-reinstall "numpy==1.26.4" "nlopt==2.7.1"

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
