from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

query_region_table = Table('query_region', Base.metadata,
	                       Column('query_id', Integer, ForeignKey('query.id')),
	                       Column('region_osm_id', Integer, ForeignKey('region.osm_id')))


class Region(Base):
	__tablename__ = 'region'

	osm_id = Column(Integer, primary_key=True)
	place_rank = Column(Integer)
	json = Column(String)


class Query(Base):
	__tablename__ = 'query'

	id = Column(Integer, primary_key=True)
	search_string = Column(String)

	regions = relationship('Region', secondary=query_region_table)