"""Celery tasks for async processing."""
import logging
from celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(bind=True, name='convert_excel_task')
def convert_excel_task(self, file_path: str, output_folder: str, expert_settings=None):
    """
    Async task to convert Excel to XML (ST26 format).

    Args:
        file_path: Path to the uploaded Excel file
        output_folder: Directory to save the generated XML
        expert_settings: Optional expert mode settings

    Returns:
        Tuple of (xml_filename, sequence_summary, reminders)
    """
    try:
        from st26autonew import convert_excel_to_xml

        logger.info(f'Starting conversion task for file: {file_path}')
        if expert_settings:
            logger.info(f'Using expert settings: {expert_settings}')

        self.update_state(state='PROGRESS', meta={
            'current': 10,
            'total': 100,
            'stage': '正在读取Excel文件',
            'processed_sequences': 0,
            'total_sequences': 0
        })

        xml_file_name, sequence_summary, reminders = convert_excel_to_xml(
            file_path, output_folder, expert_settings
        )

        logger.info(f'Conversion completed successfully, generated XML: {xml_file_name}')

        return xml_file_name, sequence_summary, reminders

    except Exception as e:
        logger.error(f'Conversion task failed: {str(e)}', exc_info=True)
        return {
            'status': 'error',
            'error_message': str(e)
        }


@celery.task(bind=True, name='blast_search_task')
def blast_search_task(self, target_sequence: str):
    """
    Async task to perform BLAST search on NCBI.

    Args:
        target_sequence: The DNA/RNA sequence to search

    Returns:
        List of BLAST results
    """
    logger.info(f'Starting BLAST search for target sequence')

    try:
        from Bio.Blast import NCBIWWW, NCBIXML

        self.update_state(state='PROGRESS', meta={'current': 0, 'total': 100})

        result_handle = NCBIWWW.qblast(
            program='blastn',
            database='nt',
            sequence=target_sequence,
            expect=0.01,
            hitlist_size=5
        )

        blast_records = NCBIXML.parse(result_handle)
        blast_results = []

        for blast_record in blast_records:
            for alignment in blast_record.alignments:
                for hsp in alignment.hsps:
                    accession = alignment.accession
                    description = alignment.title

                    result = {
                        "ncbi_id": accession,
                        "description": description,
                        "match_length": hsp.align_length,
                        "identity": hsp.identities,
                        "identity_percent": (hsp.identities / hsp.align_length) * 100,
                        "evalue": hsp.expect,
                        "query_start": hsp.query_start,
                        "query_end": hsp.query_end,
                        "subject_start": hsp.sbjct_start,
                        "subject_end": hsp.sbjct_end,
                        "query_sequence": hsp.query,
                        "subject_sequence": hsp.sbjct,
                        "alignment_sequence": hsp.match
                    }
                    blast_results.append(result)

        logger.info(f'BLAST search completed, found {len(blast_results)} matches')

        try:
            result_handle.close()
        except Exception:
            pass

        return blast_results

    except Exception as e:
        logger.error(f'BLAST search task failed: {str(e)}', exc_info=True)
        return []


def init_celery(app):
    """Initialize Celery with Flask app configuration."""
    celery.conf.update(app.config)
