ARG BASE_IMAGE=benchmark-base:qiskit_nature_787_799
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_787_799
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/787
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/799
ENV BASE_COMMIT=d1b5e0714b8e51bf28b4bd4c34eb0d7dfd0c504c
ENV PATCHED_COMMIT=5460a1d84dd0bebaa95215c34eccc30fdcb5021e
ENV PR_HEAD_COMMIT=5460a1d84dd0bebaa95215c34eccc30fdcb5021e
ENV FAIL_PASS_TEST_PATHS="test/second_q/formats/fcidump/test_fcidump.py::TestFCIDumpH2::test_electronic_energy test/second_q/formats/fcidump/test_fcidump.py::TestFCIDumpH2::test_particle_number test/second_q/formats/fcidump/test_fcidump.py::TestFCIDumpLiH::test_electronic_energy test/second_q/formats/fcidump/test_fcidump.py::TestFCIDumpLiH::test_particle_number test/second_q/formats/fcidump/test_fcidump.py::TestFCIDumpOH::test_electronic_energy test/second_q/formats/fcidump/test_fcidump.py::TestFCIDumpOH::test_particle_number test/second_q/formats/fcidump/test_methods_fcidump.py::TestMethodsFCIDump::test_lih test/second_q/formats/fcidump/test_methods_fcidump.py::TestMethodsFCIDump::test_lih_freeze_core test/second_q/formats/fcidump/test_methods_fcidump.py::TestMethodsFCIDump::test_oh test/second_q/formats/fcidump/test_methods_fcidump.py::TestMethodsFCIDump::test_oh_freeze_core test/second_q/formats/fcidump/test_methods_fcidump.py::TestFCIDumpResult::test_result_log test/second_q/formats/fcidump/test_methods_fcidump.py::TestFCIDumpResult::test_result_log_with_atoms test/second_q/formats/fcidump/test_fcidump_dumper.py::TestFCIDumpDumpH2::test_dumped_h1 test/second_q/formats/fcidump/test_fcidump_dumper.py::TestFCIDumpDumpH2::test_dumped_h2 test/second_q/formats/fcidump/test_fcidump_dumper.py::TestFCIDumpDumpH2::test_dumped_inactive_energy test/second_q/formats/fcidump/test_fcidump_dumper.py::TestFCIDumpDumpH2::test_dumped_num_electrons test/second_q/formats/fcidump/test_fcidump_dumper.py::TestFCIDumpDumpH2::test_dumped_num_molecular_orbitals test/second_q/formats/fcidump/test_fcidump_dumper.py::TestFCIDumpDumpH2::test_dumped_orbital_syms test/second_q/formats/fcidump/test_fcidump_dumper.py::TestFCIDumpDumpH2::test_dumped_spin_number test/second_q/formats/fcidump/test_fcidump_dumper.py::TestFCIDumpDumpH2::test_dumped_wave_function_sym"
ENV PASS_PASS_TEST_PATHS="test/second_q/formats/test_qcschema.py::TestQCSchemaJSON::test_from_json_1 test/second_q/formats/test_qcschema.py::TestQCSchemaJSON::test_from_json_2 test/second_q/formats/test_qcschema.py::TestQCSchemaJSON::test_from_json_3 test/second_q/formats/test_qcschema.py::TestQCSchemaJSON::test_from_json_4 test/second_q/formats/test_qcschema.py::TestQCSchemaJSON::test_to_json test/second_q/formats/test_qcschema.py::TestQCSchemaLegacy::test_legacy_from_hdf5"
ENV FAIL_PASS_EXTRA_FILES="test/second_q/formats/fcidump/__init__.py test/second_q/formats/fcidump/test_fcidump_h2.fcidump test/second_q/formats/fcidump/test_fcidump_lih.fcidump test/second_q/formats/fcidump/test_fcidump_lih.npz test/second_q/formats/fcidump/test_fcidump_oh.fcidump test/second_q/formats/fcidump/test_fcidump_oh.npz"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
