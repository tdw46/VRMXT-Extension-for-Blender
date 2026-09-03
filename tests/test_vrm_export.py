from types import SimpleNamespace

from io_scene_vrmxt.vrm_export import _SelectionTransaction, _invoke_host_export


class _Property:
    def __init__(self, identifier):
        self.identifier = identifier


class _ExportOperator:
    def __init__(self):
        self.calls = []
        self._properties = tuple(
            _Property(name)
            for name in (
                "filepath",
                "use_addon_preferences",
                "export_only_selections",
                "export_invisibles",
            )
        )

    def get_rna_type(self):
        return SimpleNamespace(properties=self._properties)

    def __call__(self, execution_context, **keywords):
        self.calls.append((execution_context, keywords))
        return {"FINISHED"}


def _context(*, selected_only=True, export_invisibles=True):
    host_preferences = SimpleNamespace(
        export_only_selections=selected_only,
        export_invisibles=export_invisibles,
    )
    return SimpleNamespace(
        preferences=SimpleNamespace(
            addons=(SimpleNamespace(preferences=host_preferences),)
        )
    )


def test_relationship_export_forces_complete_material_graph():
    operator = _ExportOperator()

    result = _invoke_host_export(
        operator,
        "/tmp/avatar.vrm",
        context=_context(selected_only=True, export_invisibles=True),
        require_complete_material_graph=True,
    )

    assert result == {"FINISHED"}
    assert operator.calls == [
        (
            "EXEC_DEFAULT",
            {
                "filepath": "/tmp/avatar.vrm",
                "use_addon_preferences": False,
                "export_only_selections": False,
                "export_invisibles": True,
            },
        )
    ]


def test_plain_export_keeps_host_preference_authority():
    operator = _ExportOperator()

    _invoke_host_export(
        operator,
        "/tmp/avatar.vrm",
        context=_context(),
        require_complete_material_graph=False,
    )

    assert operator.calls == [
        (
            "EXEC_DEFAULT",
            {
                "filepath": "/tmp/avatar.vrm",
                "use_addon_preferences": True,
            },
        )
    ]


class _Object:
    def __init__(self, name, selected=False):
        self.name = name
        self.selected = selected

    def select_set(self, selected):
        self.selected = bool(selected)


class _Objects(list):
    def __init__(self, values, active=None):
        super().__init__(values)
        self.active = active

    def values(self):
        return list(self)

    def __contains__(self, value):
        if isinstance(value, str):
            return any(obj.name == value for obj in self)
        return super().__contains__(value)


def test_selection_transaction_restores_active_and_selected_objects():
    writer = _Object("Writer", selected=True)
    reader = _Object("Reader")
    objects = _Objects([writer, reader], active=writer)
    context = SimpleNamespace(
        selected_objects=(writer,),
        view_layer=SimpleNamespace(objects=objects),
    )
    transaction = _SelectionTransaction(context)

    writer.selected = False
    reader.selected = True
    objects.active = reader
    transaction.close()

    assert writer.selected is True
    assert reader.selected is False
    assert objects.active is writer
