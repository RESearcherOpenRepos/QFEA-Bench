ARG BASE_IMAGE=benchmark-base:qiskit_nature_477_481
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_477_481
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/477
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/481
ENV BASE_COMMIT=57438121a0b3ba88304d5aed0231a50eae88a217
ENV PATCHED_COMMIT=4a0ab6bdd0314dd0848ea3903df085da90b93010
ENV PR_HEAD_COMMIT=4a0ab6bdd0314dd0848ea3903df085da90b93010
ENV FAIL_PASS_TEST_PATHS="test/drivers/second_quantization/test_driver_molecule.py::TestMolecule::test_construct"
ENV PASS_PASS_TEST_PATHS="test/drivers/second_quantization/test_driver_molecule.py::TestMolecule::test_charge test/drivers/second_quantization/test_driver_molecule.py::TestMolecule::test_multiplicity test/drivers/second_quantization/test_driver_molecule.py::TestMolecule::test_stretch test/drivers/second_quantization/test_driver_molecule.py::TestMolecule::test_bend test/drivers/second_quantization/test_driver_molecule.py::TestMolecule::test_perturbations"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
