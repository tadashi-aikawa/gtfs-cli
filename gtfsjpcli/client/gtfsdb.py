#!/usr/bin/env python

import csv
import json
import os
import sys
from typing import List, Optional, Iterable

from halo import Halo
from owlmixin import TList, TOption, TIterator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from gtfsjpcli.client.gtfs import Agency, Stop
from gtfsjpcli.client.gtfs import GtfsClient
from gtfsjpcli.dao.agency import AgencyDao
from gtfsjpcli.dao.entities import (
    BASE,
    StopEntity,
    StopTimeEntity,
    AgencyEntity,
    AgencyJpEntity,
    CalendarEntity,
    RouteEntity,
    RouteJpEntity,
    TripEntity,
    OfficeJpEntity,
    FareRuleEntity,
    FareAttributeEntity,
    CalendarDateEntity,
    ShapeEntity,
    FeedInfoEntity,
    TranslationEntity,
)
from gtfsjpcli.dao.route import RouteDao
from gtfsjpcli.dao.stop import StopDao
from gtfsjpcli.dao.trip import TripDao
from gtfsjpcli.utils.dicts import fill_none_if_empty

ENTITIES = [
    {"file": "agency.txt", "clz": AgencyEntity},
    {"file": "agency_jp.txt", "clz": AgencyJpEntity},
    {"file": "routes.txt", "clz": RouteEntity},
    {"file": "routes_jp.txt", "clz": RouteJpEntity},
    {"file": "trips.txt", "clz": TripEntity},
    {"file": "office_jp.txt", "clz": OfficeJpEntity},
    {"file": "stops.txt", "clz": StopEntity},
    {"file": "stop_times.txt", "clz": StopTimeEntity},
    {"file": "calendar.txt", "clz": CalendarEntity},
    {"file": "calendar_dates.txt", "clz": CalendarDateEntity},
    {"file": "fare_attributes.txt", "clz": FareAttributeEntity},
    {"file": "fare_rules.txt", "clz": FareRuleEntity},
    {"file": "shapes.txt", "clz": ShapeEntity},
    {"file": "feed_info.txt", "clz": FeedInfoEntity},
    {"file": "translations.txt", "clz": TranslationEntity},
]


def load_csvf(
    fpath: str,
    fieldnames: Optional[List[str]],
    encoding: str = "utf-8",
    drop_duplicates: bool = False,
) -> Iterable[dict]:
    """CSVファイルを読み込みます

    Args:
        fpath: CSVファイルのパス
        fieldnames: カラム名 (Noneの場合はヘッダの値を使用します)
        encoding: エンコーディング
        drop_duplicates: 完全重複するレコードを削除するかどうか
    """
    with open(fpath, mode="r", encoding=encoding) as f:
        snippet = f.read(8192)
        f.seek(0)

        dialect = csv.Sniffer().sniff(snippet)
        dialect.skipinitialspace = True
        it = csv.DictReader(f, fieldnames=fieldnames, dialect=dialect)

        if not drop_duplicates:
            yield from it
        else:
            sorted_list = sorted(it, key=lambda x: json.dumps(x, ensure_ascii=False))
            previous: str = None
            for current in sorted_list:
                if drop_duplicates and current == previous:
                    continue
                yield current
                previous = current


def to_agency(record: AgencyEntity) -> "Agency":
    return Agency.from_dict(
        {
            "id": record.agency_id,
            "name": record.agency_name,
            "zip_number": record.jp.agency_zip_number if record.jp else None,
            "president_name": record.jp.agency_president_name if record.jp else None,
        }
    )


def to_agencies(records: Iterable[AgencyEntity]) -> "TList[Agency]":
    return TList(records).map(to_agency)


def to_stop(record: StopEntity, with_trips: bool) -> "Stop":
    return Stop.from_dict(
        {
            "id": record.stop_id,
            "name": record.translation_ja.translation,
            "kana": record.translation_kana.translation,
            "en_name": record.translation_en.translation,
            "trip_ids": TIterator(record.stop_times).map(lambda x: x.trip_id).uniq().to_list()
            if with_trips
            else None,
        }
    )


def to_stops(records: Iterable[StopEntity], with_trips: bool) -> "TIterator[Stop]":
    return TIterator(records).map(lambda x: to_stop(x, with_trips))


class GtfsDbClient(GtfsClient):
    engine: any
    session: Session

    agency: AgencyDao
    stop: StopDao
    route: RouteDao
    trip: TripDao

    def __init__(self, source: str = "gtfs-jp.sqlite3"):
        # pylint: disable=super-init-not-called
        connection_string = source or ":memory:"
        self.engine = create_engine(f"sqlite:///{connection_string}", echo=False)
        self.session: Session = sessionmaker(bind=self.engine)()

        self.agency = AgencyDao(self.session)
        self.route = RouteDao(self.session)
        self.stop = StopDao(self.session)
        self.trip = TripDao(self.session)

    def drop_and_create(
        self, gtfs_dir: str, *, encoding: str = "utf_8_sig", drop_duplicates: bool = False
    ):
        self.__drop_database()
        self.__create_database_with_inserts(gtfs_dir, encoding, drop_duplicates)

    def find_stop_by_id(self, id_: str, with_trips: bool) -> TOption[Stop]:
        return TOption(self.stop.find_by_id(id_)).map(lambda x: to_stop(x, with_trips))

    def search_stops_by_name(self, name: str, with_trips: bool) -> TIterator[Stop]:
        return to_stops(self.stop.search_by_name(name), with_trips)

    def fetch_agencies(self) -> TList[Agency]:
        return to_agencies(self.agency.all())

    def __create_database_with_inserts(self, gtfs_dir: str, encoding: str, drop_duplicates: bool):
        BASE.metadata.create_all(self.engine)
        for e in [x for x in ENTITIES if os.path.exists(os.path.join(gtfs_dir, x["file"]))]:
            self.__insert_records(gtfs_dir, e["clz"], e["file"], encoding, drop_duplicates)
        self.session.commit()

    def __drop_database(self):
        BASE.metadata.drop_all(self.engine)

    # pylint: disable=too-many-arguments
    def __insert_records(
        self, gtfs_dir: str, clz, file_name: str, encoding: str, drop_duplicates: bool
    ):
        spinner = Halo(text=f"{file_name:<20} -- Loading", spinner="dots", stream=sys.stderr)

        spinner.start()
        dicts = [
            fill_none_if_empty(x)
            for x in load_csvf(
                os.path.join(gtfs_dir, file_name),
                fieldnames=None,
                encoding=encoding,
                drop_duplicates=drop_duplicates,
            )
        ]
        spinner.stop()

        if dicts:
            spinner.start(f"{file_name:<20} -- Insert {len(dicts)} records to `{clz.__table__}`")
            # スピード優先でcoreを使う
            self.session.execute(clz.__table__.insert(), dicts)
            spinner.succeed()
        else:
            spinner.warn(f"{file_name:<19} -- Skip to insert because there are no records.")
