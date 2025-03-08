class TestInit:
    def test__version(self):
        from one_patch import __version__
        assert __version__ == '1.0.3'
