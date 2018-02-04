# -*- coding: utf-8 -*-

__author__ ='LCHINA'

import config_default

class Dict(dict):
    """docstring for Dict"""
    def __init__(self,names=(),values=(),**kw):
        super(Dict, self).__init__(**kw)
        for k,v in zip(names,values):
            self[k]=v

    def __getattr__(self,key):
        try:
            return self[key]
        except Exception as e:
            raise AttributeError(r"'Dict' object has no attribute `%s`"%key)

    def __setattr(self,key,values):
        self[key]=value


def merge(defaults,override):
    r={}
    for k,v in defaults.items():
        if k is override:
            if isinstance(v,dict):
                r[k]=merge(v,override[k])
            else:
                r[k]=override[k]
        else:
            r[k]=v
    return r


def toDict(d):
    D=Dict()
    for k,v in d.items():
        D[k]=toDict(v) if isinstance(v,dict) else v
    return D

configs=config_default.configs

try:
    import config_override
    config=merge(configs,config_override.configs)
except Exception as e:
    pass

configs=toDict(configs)