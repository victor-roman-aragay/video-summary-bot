"""Tests for utils.logger"""

import logging
from video_summary_bot.utils.logger import setup_logger


class TestSetupLogger:
    """Tests for the setup_logger function"""

    def test_returns_logger_instance(self):
        logger = setup_logger("test_logger")
        assert isinstance(logger, logging.Logger)

    def test_logger_has_correct_name(self):
        logger = setup_logger("my_custom_logger")
        assert logger.name == "my_custom_logger"

    def test_logger_has_stream_handler(self):
        logger = setup_logger("test_handler_check")
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_logger_has_correct_format(self):
        logger = setup_logger("test_format_check")
        handler = logger.handlers[0]
        assert handler.formatter is not None
        # The formatter's _fmt should contain the expected pattern
        assert "%(asctime)s" in handler.formatter._fmt
        assert "%(name)s" in handler.formatter._fmt
        assert "%(levelname)s" in handler.formatter._fmt
        assert "%(message)s" in handler.formatter._fmt

    def test_logger_level_is_info_by_default(self):
        logger = setup_logger("test_level_default")
        assert logger.level == logging.INFO

    def test_logger_custom_level(self):
        logger = setup_logger("test_custom_level", level=logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_logger_custom_level_warning(self):
        logger = setup_logger("test_warning_level", level=logging.WARNING)
        assert logger.level == logging.WARNING

    def test_clears_duplicate_handlers(self):
        """Calling setup_logger twice should not accumulate handlers"""
        name = "test_no_dupes"
        logger1 = setup_logger(name)
        logger2 = setup_logger(name)
        assert len(logger2.handlers) == 1

    def test_logger_outputs_to_stdout(self, capsys):
        logger = setup_logger("test_output")
        logger.info("test message")
        captured = capsys.readouterr()
        assert "test message" in captured.out
