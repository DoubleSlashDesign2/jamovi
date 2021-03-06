
from .transform import Transform
from .column import Column
from .analyses import Analyses
from .utils import NullLog
from ..core import ColumnType


class InstanceModel:

    N_VIRTUAL_COLS = 5
    N_VIRTUAL_ROWS = 50

    def __init__(self):
        self._dataset = None
        self._analyses = Analyses()
        self._path = ''
        self._title = ''
        self._import_path = ''
        self._embedded_path = ''
        self._embedded_name = ''
        self._edit_tracking_suspended = True

        self._columns = [ ]
        self._transforms = [ ]
        self._next_id = 1  # an id of zero is unasigned... zero is reserved for 'no column'
        self._transform_next_id = 1  # an id of zero is unasigned... zero is reserved for 'no transform'

        self._log = NullLog()

    def __getitem__(self, index_or_name):
        if type(index_or_name) is int:
            index = index_or_name
            return self._columns[index]
        else:
            name = index_or_name
            for column in self:
                if column.name == name:
                    return column
            else:
                raise KeyError(name)

    def __iter__(self):
        return self._columns.__iter__()

    def set_log(self, log):
        self._log = log

    def get_column_by_id(self, id):
        for column in self:
            if column.id == id:
                return column
        else:
            raise KeyError('No such column: ' + str(id))

    def get_transform_by_id(self, id):
        for transform in self.transforms:
            if transform.id == id:
                return transform
        else:
            raise KeyError('No such transform: ' + str(id))

    def is_parent_of(self, parent, column, deep):
        if column.parent_id == parent.id:
            return True
        elif deep and column.parent_id > 0:
            return self.is_parent_of(parent, self.get_column_by_id(column.parent_id), True)
        else:
            return False

    def has_circular_parenthood(self, column):
        return self.is_parent_of(column, column, True)

    def remove_transform(self, id):
        i = 0
        transform = None
        while i < len(self._transforms):
            transform = self._transforms[i]
            if transform.id == id:
                del self._transforms[i]
                break
            else:
                i += 1
        return transform

    def append_transform(self, name, id=0, colour_index=0):
        use_id = self._transform_next_id
        if id != 0:
            if id < self._transform_next_id:
                for existing_transform in self.transforms:
                    if existing_transform.id == id:
                        raise KeyError('Transform id already exists: ' + str(id))
            elif id > self._transform_next_id:
                self._transform_next_id = id
            use_id = id

        new_transform = Transform(self)
        new_transform.id = use_id
        self.set_transform_name(new_transform, name)
        self.set_transform_colour_index(new_transform, colour_index)

        if use_id == self._transform_next_id:
            self._transform_next_id += 1
        self._transforms.append(new_transform)

        return new_transform

    def set_column_name(self, column, name):
        if name == '':
            filter_count = self.filter_column_count
            nIndex = column.index
            if column.index >= filter_count:
                nIndex = column.index - filter_count
            name = self._gen_column_name(nIndex)

        checked_name = name
        i = 2
        while self.check_for_column_name(checked_name, column):
            checked_name = name + ' (' + str(i) + ')'
            i += 1
        changed = column.name != checked_name
        column.name = checked_name

        return changed

    def set_transform_name(self, transform, name):
        if name == '':
            name = 'Transform ' + str(len(self._transforms) + 1)
        checked_name = name
        i = 2
        while self.check_for_transform_name(checked_name, transform):
            checked_name = name + ' (' + str(i) + ')'
            i += 1
        changed = transform.name != checked_name
        transform.name = checked_name

        return changed

    def set_transform_colour_index(self, transform, colour_index):
        if colour_index < 0 or self.check_for_transform_colour_index(colour_index, transform):
            colour_index = 0

        while self.check_for_transform_colour_index(colour_index, transform):
            colour_index += 1

        transform.colour_index = colour_index

    def check_for_transform_colour_index(self, colour_index, exclude_transform):
        for existing_transform in self.transforms:
            if colour_index == existing_transform.colour_index and existing_transform is not exclude_transform:
                return True

        return False

    def check_for_transform_name(self, name, exclude_transform):
        for existing_transform in self.transforms:
            if name == existing_transform.name and existing_transform is not exclude_transform:
                return True

        return False

    def check_for_column_name(self, name, exclude_column):
        for existing_column in self:
            if name == existing_column.name and existing_column is not exclude_column:
                return True

        return False

    def append_column(self, name, import_name=None, id=0):
        use_id = self._next_id
        if id != 0:
            if id < self._next_id:
                for existing_column in self:
                    if existing_column.id == id:
                        raise KeyError('Column id already exists: ' + str(id))
            elif id > self._next_id:
                self._next_id = id
            use_id = id

        column = self._dataset.append_column(name, import_name)
        column.column_type = ColumnType.NONE
        column.id = use_id

        if use_id == self._next_id:
            self._next_id += 1

        new_column = Column(self, column)
        new_column.index = self.total_column_count
        self._columns.append(new_column)
        return new_column

    def begin_edit_tracking(self):
        self._edit_tracking_suspended = False

    def set_cells_as_edited(self, column, row_start, row_end):
        if self._edit_tracking_suspended is False:
            column.cell_tracker.set_cells_as_edited(row_start, row_end)

    def set_row_count(self, count):
        if self._edit_tracking_suspended is False:
            if count > self._dataset.row_count:
                for column in self:
                    if column.column_type == ColumnType.DATA:
                        column.cell_tracker.insert_rows(self._dataset.row_count, count - 1)
        self._dataset.set_row_count(count)

    def delete_rows(self, start, end):
        self._dataset.delete_rows(start, end)
        if self._edit_tracking_suspended is False:
            for column in self:
                column.cell_tracker.remove_rows(start, end)
        self._recalc_all()

    def insert_rows(self, start, end):
        self._dataset.insert_rows(start, end)
        for column in self:
            if column.column_type == ColumnType.DATA:
                column.cell_tracker.insert_rows(start, end)
        self._recalc_all()

    def insert_column(self, index, id=0):
        if id != 0:
            if id < self._next_id:
                for existing_column in self:
                    if existing_column.id == id:
                        raise KeyError('Column id already exists: ' + str(id))
            self._next_id = id

        filter_count = self.filter_column_count

        nIndex = index
        if index >= filter_count:
            nIndex = index - filter_count
        name = self._gen_column_name(nIndex)

        ins = self._dataset.insert_column(index, name)
        ins.auto_measure = True
        ins.id = self._next_id
        self._next_id += 1

        child = self._dataset[index]
        column = Column(self, child)
        column.column_type = ColumnType.NONE
        self._columns.insert(index, column)

        index = 0
        for column in self:
            column.index = index
            index += 1

    def update_filter_names(self):
        filter_index = 0
        subfilter_index = 1
        filters = []

        for column in self._columns:
            if column.column_type is not ColumnType.FILTER:
                break
            if column.filter_no in filters:
                column.name = 'F{} ({})'.format(filter_index, subfilter_index + 1)
                column.filter_no = filter_index - 1
                subfilter_index += 1
            else:
                column.name = 'Filter {}'.format(filter_index + 1)
                if column.filter_no > -1:
                    filters.append(column.filter_no)
                column.filter_no = filter_index
                filter_index += 1
                subfilter_index = 1

    def update_filter_status(self):
        self._dataset.update_filter_status()

    def delete_columns(self, start, end):
        self._dataset.delete_columns(start, end)
        del self._columns[start:end + 1]

        for i in range(start, len(self._columns)):
            self._columns[i].index = i

        self.update_filter_names()

    def delete_columns_by_id(self, ids):
        sortedIds = sorted(ids, key=lambda id: self.get_column_by_id(id).index)

        start = -1
        end = -1
        for i in range(0, len(sortedIds)):
            column = self.get_column_by_id(sortedIds[i])
            if start == -1:
                start = column.index
                end = start
            elif column.index == end + 1:
                end += 1
            else:
                self.delete_columns(start, end)
                start = column.index
                end = start

        if start is not -1:
            self.delete_columns(start, end)

        self.update_filter_names()

    def is_row_filtered(self, index):
        if index < self._dataset.row_count:
            return self._dataset.is_row_filtered(index)
        else:
            return False

    @property
    def has_edited_cells(self):
        for column in self._columns:
            if column.is_edited:
                return True
        return False

    @property
    def transforms(self):
        return self._transforms

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, title):
        self._title = title

    @property
    def analyses(self):
        return self._analyses

    @property
    def has_dataset(self):
        return self._dataset is not None

    @property
    def dataset(self):
        return self._dataset

    @dataset.setter
    def dataset(self, dataset):
        self._dataset = dataset

    def setup(self):

        self._next_id = 1

        index = 0
        for child in self._dataset:
            if index < len(self._columns):
                column = self._columns[index]
            else:
                column = Column(self, child)
                self._columns.append(column)
            column.index = index

            index += 1

            if column.id >= self._next_id:
                self._next_id = column.id + 1

        for transform in self._transforms:
            transform.parse_formula()

        for column in self:
            if column.column_type is not ColumnType.DATA:
                column.parse_formula()

        self._add_virtual_columns()

    def _add_virtual_columns(self):
        n_virtual = self.total_column_count - self.column_count
        for i in range(n_virtual, InstanceModel.N_VIRTUAL_COLS):
            index = self.total_column_count
            column = Column(self)
            column.id = self._next_id
            column.index = index
            self._columns.append(column)
            self._next_id += 1

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        self._path = path

    @property
    def import_path(self):
        return self._import_path

    @import_path.setter
    def import_path(self, path):
        self._import_path = path

    @property
    def embedded_path(self):
        return self._embedded_path

    @embedded_path.setter
    def embedded_path(self, path):
        self._embedded_path = path

    @property
    def embedded_name(self):
        return self._embedded_name

    @embedded_name.setter
    def embedded_name(self, name):
        self._embedded_name = name

    def index_from_visible_index(self, d_index):
            count = -1
            i = 0
            for column in self._columns:
                i += 1
                if column.hidden is False:
                    count += 1
                if count == d_index:
                    return column.index
            return -1

    @property
    def virtual_row_count(self):
        return self._dataset.row_count + InstanceModel.N_VIRTUAL_ROWS

    @property
    def virtual_column_count(self):
        return self.total_column_count - self.column_count

    @property
    def visible_column_count(self):
        count = 0
        for column in self._columns:
            if column.hidden is False:
                count += 1
        return count

    @property
    def filter_column_count(self):
        count = 0
        for column in self._columns:
            if column.column_type == ColumnType.FILTER:
                count += 1
            else:
                break
        return count

    @property
    def total_column_count(self):
        return len(self._columns)

    @property
    def row_count(self):
        return self._dataset.row_count

    @property
    def column_count(self):
        return self._dataset.column_count

    @property
    def is_edited(self):
        return self._dataset.is_edited

    @is_edited.setter
    def is_edited(self, edited):
        self._dataset.is_edited = edited

    @property
    def is_blank(self):
        return self._dataset.is_blank

    @is_blank.setter
    def is_blank(self, blank):
        self._dataset.blank = blank

    def get_column_count_by_type(self, columnType):
        count = 0
        for column in self._columns:
            if column.column_type == columnType:
                count += 1
        return count

    def _gen_column_name(self, index):
        name = ''
        while True:
            i = index % 26
            name = chr(i + 65) + name
            index -= i
            index = int(index / 26)
            index -= 1
            if index < 0:
                break

        i = 2
        try_name = name
        while True:
            for column in self._dataset:
                if column.name == try_name:
                    break  # not unique
            else:
                name = try_name
                break  # unique
            try_name = name + ' (' + str(i) + ')'
            i += 1
        return name

    def _realise_column(self, column):
        index = column.index
        filter_count = self.filter_column_count
        for i in range(self.column_count, index + 1):
            name = self._gen_column_name(i - filter_count)
            child = self._dataset.append_column(name)
            wrapper = self[i]
            child.id = wrapper.id
            wrapper._child = child
            wrapper.auto_measure = True
        self._add_virtual_columns()

    def _recalc_all(self):
        for column in self:
            column.set_needs_recalc()
        for column in self:
            column.recalc()

    def _print_column_info(self):
        for column in self:
            if column.has_deps:
                depts = list(map(lambda x: x.name, column.dependents))
                depcs = list(map(lambda x: x.name, column.dependencies))

                self._log.debug('Column: {}'.format(column.name))
                self._log.debug('  Needs recalc: {}'.format(column.needs_recalc))
                self._log.debug('  With dependencies:')
                self._log.debug('    {}'.format(depcs))
                self._log.debug('  With dependents:')
                self._log.debug('    {}'.format(depts))
