import io
import os
import pathlib
from contextlib import AbstractContextManager, contextmanager
from types import TracebackType
from typing import (
    IO,
    Any,
    AnyStr,
    Callable,
    ContextManager,
    Generic,
    Iterator,
    Mapping,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)


ArchiveType = TypeVar('ArchiveType', bound='BaseArchive')
EntryType = TypeVar('EntryType')
ArchiveIndex = Mapping[str, EntryType]


def create_directory(name: AnyStr) -> None:
    os.makedirs(name, exist_ok=True)


class _SimpleEntry(NamedTuple):
    offset: int
    size: int


SimpleEntry = Union[_SimpleEntry, Tuple[int, int]]


def read_file(stream: IO[bytes], offset: int, size: int) -> bytes:
    stream.seek(
        offset, io.SEEK_SET
    )  # need unit test to check offset is always equal to f.tell()
    return stream.read(size)


class BaseArchive(AbstractContextManager, Generic[EntryType]):
    _stream: IO[bytes]

    index: Mapping[str, EntryType]

    def _create_index(self) -> ArchiveIndex[EntryType]:
        raise NotImplementedError('create_index')

    def _read_entry(self, entry: EntryType) -> bytes:
        raise NotImplementedError('read_entry')

    def __init__(self, file: Union[AnyStr, os.PathLike[AnyStr], IO[bytes]]) -> None:
        if isinstance(file, os.PathLike):
            file = os.fspath(file)

        if isinstance(file, (str, bytes)):
            self._stream = io.open(file, 'rb')
        else:
            self._stream = file
        self.index = self._create_index()

    @contextmanager
    def open(self, fname: str, mode: str = 'r') -> Iterator[IO]:
        if not fname in self.index:
            raise ValueError(f'no member {fname} found in archive')

        data = self._read_entry(self.index[fname])

        stream: IO
        with io.BytesIO(data) as stream:
            if not 'b' in mode:
                stream = io.TextIOWrapper(stream, encoding='utf-8')
            yield stream

    def close(self) -> Optional[bool]:
        return self._stream.close()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Optional[bool]:
        return self.close()

    def __iter__(self) -> Iterator[Tuple[str, bytes]]:
        for fname, entry in self.index.items():
            yield fname, self._read_entry(entry)

    def glob(self, pattern: str) -> Iterator[str]:
        return (fname for fname in self.index if pathlib.Path(fname).match(pattern))

    def extractall(self, dirname: str) -> None:
        create_directory(dirname)
        for fname, filedata in self:
            with io.open(os.path.join(dirname, fname), 'wb') as out_file:
                out_file.write(filedata)


class SimpleArchive(BaseArchive[SimpleEntry]):
    def _read_entry(self, entry: SimpleEntry) -> bytes:
        entry = _SimpleEntry(*entry)
        return read_file(self._stream, entry.offset, entry.size)


def make_opener(
    archive_type: Type[ArchiveType],
) -> Callable[..., ContextManager[ArchiveType]]:
    @contextmanager
    def opener(*args: Any, **kwargs: Any) -> Iterator[ArchiveType]:
        with archive_type(*args, **kwargs) as inst:
            yield inst

    return opener
