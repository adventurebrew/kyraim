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
    Iterator,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)


ArchiveIndex = Mapping[str, Tuple[int, int]]
ArchiveType = TypeVar('ArchiveType', bound='BaseArchive')


def create_directory(name: AnyStr) -> None:
    os.makedirs(name, exist_ok=True)


def read_file(stream: IO[bytes], offset: int, size: int) -> bytes:
    stream.seek(
        offset, io.SEEK_SET
    )  # need unit test to check offset is always equal to f.tell()
    return stream.read(size)


class BaseArchive(AbstractContextManager):
    _stream: IO[bytes]

    index: Mapping[str, Tuple[int, int]]

    def create_index(self) -> ArchiveIndex:
        raise NotImplementedError('create_index')

    def __init__(self, file: Union[AnyStr, os.PathLike[AnyStr], IO[bytes]]) -> None:
        if isinstance(file, os.PathLike):
            file = os.fspath(file)

        if isinstance(file, (str, bytes)):
            self._stream = io.open(file, 'rb')
        else:
            self._stream = file
        self.index = self.create_index()

    @contextmanager
    def open(self, fname: str, mode: str = 'r') -> Iterator[IO]:
        if not fname in self.index:
            raise ValueError(f'no member {fname} found in archive')

        start, size = self.index[fname]
        data = read_file(self._stream, start, size)

        stream: IO
        with io.BytesIO(data) as stream:
            if not 'b' in mode:
                stream = io.TextIOWrapper(stream, encoding='utf-8')
            yield stream

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Optional[bool]:
        return self._stream.close()

    def __iter__(self) -> Iterator[Tuple[str, bytes]]:
        for fname, (start, size) in self.index.items():
            yield fname, read_file(self._stream, start, size)

    def glob(self, pattern: str) -> Iterator[str]:
        return (fname for fname in self.index if pathlib.Path(fname).match(pattern))

    def extractall(self, dirname: str) -> None:
        create_directory(dirname)
        for fname, filedata in self:
            with io.open(os.path.join(dirname, fname), 'wb') as out_file:
                out_file.write(filedata)


def make_opener(
    archive_type: Type[ArchiveType],
) -> Callable[..., ContextManager[ArchiveType]]:
    @contextmanager
    def opener(*args: Any, **kwargs: Any) -> Iterator[ArchiveType]:
        with archive_type(*args, **kwargs) as inst:
            yield inst

    return opener
