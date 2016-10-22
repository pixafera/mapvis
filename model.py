from sqlalchemy import Column, Float, ForeignKey, Integer, String, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Region(Base):
	__tablename__ = 'region'

	osm_id = Column(Integer, primary_key=True)
	place_rank = Column(Integer)
	json = Column(String)

	queries = relationship('QueryRegion', backref='region')

	def to_dict(self):
		return dict(osm_id=self.osm_id,
			        place_rank=self.place_rank,
			        json=self.json)


class Query(Base):
	__tablename__ = 'query'

	id = Column(Integer, primary_key=True)
	search_string = Column(String)

	regions = relationship('QueryRegion', backref='query')

	def to_dict(self):
		return dict(id=self.id,
			        search_string=self.search_string,
			        regions=[r.to_dict() for r in self.regions])

class QueryRegion(Base):
	__tablename__ = 'query_region'

	query_id = Column(Integer, ForeignKey('query.id'), primary_key=True)
	region_osm_id = Column(Integer, ForeignKey('region.osm_id'), primary_key=True)
	importance = Column(Float)

	def to_dict(self):
		return dict(importance=self.importance, **self.region.to_dict())


class Dataset(Base):
	__tablename__ = 'dataset'

	id = Column(String, primary_key=True)
	name = Column(String)
	json = Column(String)