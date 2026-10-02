ARG BASE_IMAGE=benchmark-base:qiskit_nature_577_591
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_577_591
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/577
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/591
ENV BASE_COMMIT=2c7a298a95a1a3ad405b8f1e35dc2d1055b69eed
ENV PATCHED_COMMIT=3372bc1c19ab0e738720fcf847b338af2be3ceb2
ENV PR_HEAD_COMMIT=3e7bdb9bde5bd78f9c834a81af42507f6bd489c5
ENV FAIL_PASS_TEST_PATHS="test/problems/second_quantization/lattice/models/test_heisenberg_model.py::TestHeisenbergModel::test_init test/problems/second_quantization/lattice/models/test_heisenberg_model.py::TestHeisenbergModel::test_triangular test/problems/second_quantization/lattice/models/test_heisenberg_model.py::TestHeisenbergModel::test_ising test/problems/second_quantization/lattice/models/test_heisenberg_model.py::TestHeisenbergModel::test_xy test/problems/second_quantization/lattice/models/test_heisenberg_model.py::TestHeisenbergModel::test_xyz_ext_field"
ENV PASS_PASS_TEST_PATHS="test/problems/second_quantization/lattice/models/test_ising_model.py::TestIsingModel::test_init test/problems/second_quantization/lattice/models/test_ising_model.py::TestIsingModel::test_uniform_parameters test/problems/second_quantization/lattice/models/test_ising_model.py::TestIsingModel::test_from_parameters"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
