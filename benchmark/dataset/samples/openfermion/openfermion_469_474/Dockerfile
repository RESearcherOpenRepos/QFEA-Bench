ARG BASE_IMAGE=benchmark-base:openfermion_469_474
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=openfermion_469_474
ENV REPOSITORY=quantumlib/OpenFermion
ENV REPOSITORY_URL=https://github.com/quantumlib/OpenFermion.git
ENV ISSUE_URL=https://github.com/quantumlib/OpenFermion/issues/469
ENV PR_URL=https://github.com/quantumlib/OpenFermion/pull/474
ENV BASE_COMMIT=e3b7236b2061b8f87222fd7ab23040cb2e5a77ee
ENV PATCHED_COMMIT=8a790335cc2ac7f82c53a22f821ce51e8486e79d
ENV PR_HEAD_COMMIT=8a790335cc2ac7f82c53a22f821ce51e8486e79d
ENV FAIL_PASS_TEST_PATHS="src/openfermion/utils/_lattice_test.py::test_hubbard_square_lattice_edge_types src/openfermion/hamiltonians/_general_hubbard_test.py::test_fermi_hubbard_square_lattice_random_parameters[lattice0-parameters0-True] src/openfermion/hamiltonians/_general_hubbard_test.py::test_fermi_hubbard_square_lattice_random_parameters[lattice2-parameters2-True]"
ENV PASS_PASS_TEST_PATHS="src/openfermion/utils/_lattice_test.py::test_hubbard_square_lattice_defaults src/openfermion/utils/_lattice_test.py::test_hubbard_square_lattice_dof_validation[1] src/openfermion/utils/_lattice_test.py::test_hubbard_square_lattice_2x2 src/openfermion/hamiltonians/_general_hubbard_test.py::test_fermi_hubbard_default_parameters src/openfermion/hamiltonians/_general_hubbard_test.py::test_fermi_hubbard_bad_parameters"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
