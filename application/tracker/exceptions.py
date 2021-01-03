class TableRowsNotFound(Exception):
    def __init__(self, table, operation=None, missing=None, found=None):
        message = f"{table}(s) not found, for {operation}."
        int_or_id = lambda x: x if type(x) is int else x.id
        sort_by_ids = lambda items: sorted([x.id for x in items], key=int_or_id)
        if missing is not None:
            message += f" Missing ids: {sort_by_ids(missing)}."
        if found is not None:
            message += f" Found ids: {sort_by_ids(found)}."

        super().__init__(message)

class PetitionsNotFound(TableRowsNotFound):
    def __init__(self, operation=None, missing=None, found=None):
        super().__init__("Petition", operation, missing, found)

class RecordsNotFound(TableRowsNotFound):
    def __init__(self, operation=None, missing=None, found=None):
        super().__init__("Record", operation, missing, found)