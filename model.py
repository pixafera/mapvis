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

	def to_dict(self):
		return dict(osm_id=self.osm_id,
			        place_rank=self.place_rank,
			        json=self.json)


class Query(Base):
	__tablename__ = 'query'

	id = Column(Integer, primary_key=True)
	search_string = Column(String)

	regions = relationship('Region', secondary=query_region_table)

	def to_dict(self):
		return dict(id=self.id,
			        search_string=self.search_string,
			        regions=[r.to_dict() for r in self.regions])