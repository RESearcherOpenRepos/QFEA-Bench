FROM benchmark-base:pennylane_3982_3977

ENV SAMPLE_ID=pennylane_3982_3977
ENV REPOSITORY_URL=https://github.com/PennyLaneAI/pennylane.git
ENV BASE_COMMIT=4d549faae969b8fd8c243fcc480963ddfdb66dda
ENV PATCHED_COMMIT=258e729e3a445b2c06de45a5948e9ca1cf06d5e0
ENV FAIL_PASS_TEST_PATHS="tests/qchem/test_tapering.py::test_split_pauli_sentence[190-49] tests/qchem/test_tapering.py::test_split_pauli_sentence[40-13] tests/qchem/test_tapering.py::test_taper_obs[symbols0-geometry0-0]"
ENV PASS_PASS_TEST_PATHS="tests/qchem/test_tapering.py::test_reduced_row_echelon[binary_matrix0-result0] tests/qchem/test_tapering.py::test_kernel[binary_matrix0-result0] tests/qchem/test_tapering.py::test_generate_paulis[generators0-4-result0] tests/qchem/test_tapering.py::test_cliford[generator0-paulixops0-result0] tests/qchem/test_tapering.py::test_transform_hamiltonian[symbols0-geometry0-generator0-paulixops0-paulix_sector0-ham_ref0] tests/qchem/test_tapering.py::test_transform_hf[generators0-paulixops0-paulix_sector0-2-4-result0]"

WORKDIR /benchmark
COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
