# encoding=utf-8

import asyncio
import logging
import aiomysql


__pool=None

def log(sql,args=()):
    logging.info('SQL:%s'%sql)

async def create_pool(loop,**kw):
    logging.info('create database connection pool...')
    global __pool
    __pool=await aiomysql.create_pool(
        host=kw.get('host','localhost'),
        port=kw.get('port',3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset','utf8'),
        autocommit=kw.get('autocommit',True),
        maxsize=kw.get('maxsize',10),
        minsize=kw.get('minsize',1),
        loop=loop
        )


async def select(sql,args,size=None):
    log(sql,args)
    global __pool
    with (await __pool) as conn:
        cur=await conn.cursor(aiomysql.DictCursor)
        await cur.execute(sql.replace('?','%s'),args or ())
        if size:
            rs=await cur.fetchmany(size)
        else:
            rs=await cur.fetchall()
        await cur.close()
        logging.info('rows returned :%s'%len(rs))
        return rs


async def execute(sql,args):
    log(sql)
    affected=None
    with (await __pool) as conn:
        try:
            cur=await conn.cursor()
            await cur.execute(sql.replace('?','%s'),args)
            affected=cur.rowcount
            await cur.close()
        except Exception as e:
            raise
        return affected

def create_args_string(num):
    L= []
    for n in range(num):
        L.append('?')
    return ', '.join(L)

class Field(object):
    """docstring for Field"""
    def __init__(self, name, column_type,primary_key,default):
        self.name=name
        self.column_type=column_type
        self.primary_key=primary_key
        self.default=default

    def __str__(self):
        return '<%s,%s:%s>'%(self.__class__.__name__,self.column_type,self.name)

class StringField(Field):
    """docstring for StringField"""
    def __init__(self, name=None,primary_key=False,default=None,ddl='varchar(100)'):
        super().__init__(name,ddl,primary_key,default)

class BooleanField(Field):
    """docstring for BooleanField"""
    def __init__(self, name=None,default=False):
        super().__init__(name,'boolean',False,default)

class IntegerField(Field):
    """docstring for IntegerField"""
    def __init__(self, name=None,primary_key=False, default=0):
        super().__init__(name,'bigint',primary_key,default)

class FloatField(Field):
    """docstring for FloatField"""
    def __init__(self, name=None,primary_key=False, default=0.0):
        super().__init__(name,'real',primary_key,default)

class TextField(Field):
    """docstring for TextField"""
    def __init__(self,  name=None, default=None):
        super().__init__(name,'text',False,default)
        
        
class ModelMetaclass(type):

    def __new__(cls,name,bases,attrs):
        # 排除model 类本身
        if name=='Model':
            return type.__new__(cls,name,bases,attrs)
        #获取table名称
        tableName=attrs.get('__table__',None) or name
        logging.info('found model :%s(table : %s)'%(name,tableName))
        mapping=dict()
        fields=[]
        primaryKey=None
        for k,v in attrs.items():
            if isinstance(v,Field):
                logging.info(' found mapping:%s==>%s'%(k,v))
                mapping[k]=v
                if v.primary_key:
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field :%s'%k)
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:
            raise RuntimeError('primary key not found.')

        for k in mapping.keys():
            attrs.pop(k)
        escaped_fields=list(map(lambda f:'`%s`'%f,fields))
        attrs['__mappings__']=mapping
        attrs['__table__']=tableName
        attrs['__primary_key__']=primaryKey
        attrs['__fields__']=fields
        attrs['__select__']='select `%s` , %s from `%s`'%(primaryKey,', '.join(escaped_fields),tableName)
        attrs['__insert__']='insert into `%s` (%s ,`%s`) values (%s)'%(tableName,', '.join(escaped_fields),primaryKey,create_args_string(len(escaped_fields)+1))
        attrs['__update__']='update `%s` set %s where `%s` =? '%(tableName,', '.join(map(lambda f:'`%s`=?'%(mapping.get(f).name or f),fields)),primaryKey)
        attrs['__delete__']='delete from `%s` where `%s`=?'%(tableName,primaryKey)
        return type.__new__(cls,name,bases,attrs)     


class Model(dict,metaclass=ModelMetaclass):
    """docstring for Model"""
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self,key):
        try:
            return self[key]
        except KeyError as e:
            raise AttributeError(r"'Model' object has no attribute '%s'"%key)
    
    def __setattr(self,key,value):
        self[key]=value

    def getValue(self,key):
        return getattr(self,key,None)

    def getValueOrDefault(self,key):
        value=getattr(self,key,None)
        if value is None:
            field=self.__mappings__[key]
            if field.default is not None:
                value=field.default() if callable(field.default) else field.default
                logging.info('using default value for %s:%s'%(key,str(value)))
                setattr(self,key,value)
        return value

    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        ' find objects by where clause. '
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    async def find(cls,pk):
        'find object by primary key.'
        rs=await select('%s where `%s`=?'%(cls.__select__,cls.__primary_key__),[pk],1)
        if len(rs)==0:
            return None
        else:
            return cls(**rs[0])


    async def save(self):
        args=list(map(self.getValueOrDefault,self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows=await execute(self.__insert__,args)
        if rows!=1:
            logging.warn('field to insert record:affected rows :%s'%rows)


