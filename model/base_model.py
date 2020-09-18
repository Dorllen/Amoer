import datetime
import copy
import json


class BaseValueModel(object):
    '''自定义 值类型。用于将所有数据转换成JSON支持的数据格式'''
    # apply 运用在赋予初始值，以及后续校验
    def apply(self, value):
        '''转变方式'''
        raise NotImplemented("未实现apply方法")

    def value(self):
        '''默认值'''
        raise NotImplemented("未实现value方法")


class LimitedValueModel(BaseValueModel):
    def __init__(self, default_value):
        self.default_value = default_value

    def apply(self, value):
        self.default_value = value
        return value

    def value(self):
        return self.default_value

    def __getattr__(self, item):
        # if "value" in self.__dict__:
        #     return super().__getattribute__("value")
        # print(item)
        if item.startswith("__"):
            return super().__getattribute__(item)
        tmp_value = self.default_value
        return getattr(tmp_value, item)

    def __repr__(self):
        return super().__repr__() + "; value: %s" % repr(self.default_value)

    def __eq__(self, other):
        return self.value().__eq__(other)

    def __lt__(self, other):
        return self.value().__lt__(other)

    def __gt__(self, other):
        return self.value().__gt__(other)

    def __bool__(self):
        return self.value().__bool__()

    def __le__(self, other):
        return self.value().__le__(other)

    def __ge__(self, other):
        return self.value().__ge__(other)

    def __add__(self, other):
        return self.value() + other

    def __len__(self):
        return len(self.value())


class BetweenValueModel(LimitedValueModel):
    '''值范围限制'''
    pass


class ComplexValueModel(LimitedValueModel):
    '''更复杂的值类型约束'''
    def __init__(self, default_value=None, required=False):
        self.required = required
        super().__init__(default_value)

    def value(self):
        '''此处 bool(0) == true'''
        if self.required:
            assert self.default_value, "值约束条件不满足"
        return self.default_value


class DateTimeValueModel(ComplexValueModel):
    def __init__(self, formatter, default_value=None, required=False):
        self.formatter = formatter
        super().__init__(default_value, required)

    def apply(self, value):
        if isinstance(value, datetime.datetime):
            self.default_value = value
            return value
        elif isinstance(value, str):
            self.default_value = datetime.datetime.strptime(value, self.formatter)
            return value
        else:
            raise NotImplemented("不支持")

    def value(self):
        dt = super().value()
        if dt:
            assert isinstance(dt, datetime.datetime), "非期望值类型"
        else:
            dt = datetime.datetime.now()
        return dt.strftime(self.formatter)


class DateTimeIntValueModel(ComplexValueModel):
    '''默认时间戳 取10位'''
    def apply(self, value):
        if isinstance(value, datetime.datetime):
            self.default_value = value
            return value
        elif isinstance(value, str):
            self.default_value = datetime.datetime.strptime(value, self.default_value)
            return value
        else:
            raise NotImplemented("不支持")

    def value(self):
        dt = super().value()
        if dt:
            assert isinstance(self.default_value, datetime.datetime), "非期望值类型"
        else:
            dt = datetime.datetime.now()
        return int(dt.timestamp())


class FixedValueModel(ComplexValueModel):
    '''支持None. FixedValueModel(value_cls=str) 与 "" 不同在于，后者可以为None'''
    def __init__(self, default_value=None, required=False, value_cls=None):
        self.value_cls = value_cls
        super().__init__(default_value, required)

    def value(self):
        tmp_value = super().value()
        assert not tmp_value or isinstance(tmp_value, self.value_cls), "非期望值类型"
        return tmp_value


class ListComplexValueModel(ComplexValueModel):
    def __init__(self, default_value=None, required=False, need_size=False, value_cls=None, support_dict_value=False):
        '''
        列表约束条件
        :param default_value: 默认值
        :param required: 是否必须
        :param need_size: 长度大于0
        :param value_cls: 值class. e.g. BaseDataModel、str
        :param support_dict_value: 支持dict覆盖
        '''
        self.need_size = need_size
        self.value_cls = value_cls
        self.support_dict_value = support_dict_value
        if not default_value:
            default_value = []
        super().__init__(default_value, required)

    def value(self):
        tmp_value = super().value()
        assert isinstance(tmp_value, list), "非List类型"
        if self.required and self.need_size:
            assert len(tmp_value) > 0, "值约束条件不满足"
        if self.value_cls and tmp_value:
            for index, k in enumerate(tmp_value):
                if not isinstance(k, self.value_cls):
                    if isinstance(k, dict) and isinstance(self.value_cls(), BaseDataModel):
                        if self.support_dict_value:
                            return tmp_value
                        s0 = sorted(k.keys())
                        s1 = sorted(self.value_cls.DATA_DEFAULT_FORMAT.keys())
                        if self.value_cls.STRICT_MODE:
                            if s0 == s1:
                                return tmp_value
                        else:
                            if s1 in s0:
                                return tmp_value
                            else:
                                # 少于DATA_DEFAULT_FORMAT情况，要判断是否为required字段。暂时不支持
                                pass
                    assert False, f"{index} 不符合数据格式要求 {self.value_cls}"
        return tmp_value

    def __repr__(self):
        return super().__repr__() + " value_cls: %s" % repr(self.value_cls)


class NumberBetweenValueModel(BetweenValueModel):
    '''
    存在数字范围的 值类型
    '''
    def __init__(self, default_value, min_value, max_value):
        self.min = min_value
        self.max = max_value
        super().__init__(default_value)

    def apply(self, value):
        if self.min <= value <= self.min:
            self.default_value = value
            return value
        else:
            raise ValueError(f"数据值超出范围: [%s, %s] value: %s" % (self.min, self.max, value))


class ListBetweenValueModel(BetweenValueModel):
    '''
    存在List中的 值类型
    '''
    def __init__(self, default_value, value_list):
        self.value_list = value_list
        super().__init__(default_value)

    def apply(self, value):
        if self.value_list and value in self.value_list:
            if isinstance(self.default_value, list):
                self.default_value.append(value)
            else:
                self.default_value = [value]
            return value
        else:
            raise ValueError("数据值超出范围: %s value:%s" % (self.value_list, value))


class BaseDataModel(object):

    DATA_DEFAULT_FORMAT = {} # DATA_DEFAULT_FORMAT的values解释：{}代表BaseDataModel、type代表严格要求、其他基本数据类型有默认值0

    STRICT_MODE = False # 严格模式。 是否接收额外DATA_DEFAULT_FORMAT中未定义的key

    def __init__(self, **kwargs):
        # 检查self.DATA_DEFAULT_FORMAT 不能是禁止的方法
        self._check_key_format(self.DATA_DEFAULT_FORMAT)
        data_formatter = copy.deepcopy(self.DATA_DEFAULT_FORMAT)
        self.__dict__.update(**self.pre_new(data_formatter))
        self.update(kwargs)

    @classmethod
    def pre_new(cls, data):
        '''放各种pre_new的方法. 创建之前的方法'''
        return data

    @classmethod
    def default_value(cls, value):
        '''
        默认值生成。此值是根据 Type/Class -> 值类型.
        :param value:
        :return:
        '''
        if isinstance(value, str) or isinstance(value, str.__class__):
            return ""
        elif isinstance(value, list) or isinstance(value, list.__class__):
            return []
        elif isinstance(value, dict) or isinstance(value, dict.__class__):
            if isinstance(value, dict):
                for k, v in value.items():
                    value[k] = cls.default_value(v)
                return value
            return {}
        elif isinstance(value, int) or isinstance(value, int.__class__):
            return 0
        elif isinstance(value, float) or isinstance(value, float.__class__):
            return 0.0
        elif isinstance(value, datetime.datetime):
            return datetime.datetime.now()
        elif isinstance(value, BaseValueModel):
            return value.value()
        else:
            return None

    @classmethod
    def _check_key_format(cls, formatter):
        '''限制自定义key影响正常使用'''
        if not hasattr(cls, "_keys_limited"):
            cls._keys_limited = dir(cls)
        key_dirs = cls._keys_limited
        for _key in key_dirs:
            if (isinstance(formatter, dict) and _key in formatter) or (isinstance(formatter, str) and _key == formatter):
                raise RuntimeError("不允许formatter覆盖cls方法: %s" % formatter)

    def __setattr__(self, key, value):
        # _value = getattr(self, key) if hasattr(self, key) else None
        self._check_key_format(key)
        if self.STRICT_MODE:
            if key not in self.DATA_DEFAULT_FORMAT:
                raise RuntimeError("严格模式不支持额外字段: " + key)
        _value = self.DATA_DEFAULT_FORMAT.get(key)
        if _value is not None:
            if type(_value) == type(value):
                # 同一个类型
                super().__setattr__(key, value)
            elif type(_value) == type and isinstance(value, _value):
                # 属于_value类型
                super().__setattr__(key, value)
            elif isinstance(_value, dict) and isinstance(value, BaseDataModel): # 对于dict类型代表直接赋值
                super().__setattr__(key, value)
            elif isinstance(_value, LimitedValueModel):
                getattr(self, key).apply(value)
            elif isinstance(_value, BaseValueModel): # 直接赋值，本来BaseValueModel就是个影子对象
                super().__setattr__(key, value)
        else:
            super().__setattr__(key, value)

    # 温和更新
    def update(self, dict_value):
        if isinstance(dict_value, dict):
            for k, v in dict_value.items():
                setattr(self, k, v)
        return self

    # 强制更新
    def upgrade(self, dict_value):
        '''直接更新底层__dict__'''
        if isinstance(dict_value, dict):
            self.__dict__.update(dict_value)
        return self

    # 模拟dict[xxx]操作
    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, item):
        return getattr(self, item)

    # def __getattribute__(self, item):
    #     print("g:", item)
    #     return super().__getattribute__(item)
    #
    # def __getattr__(self, item):
    #     print("item:", item)
    #     return super().__getattribute__(item)

    @classmethod
    def _check_value(cls, k, v):
        '''数据验证/检查方法'''
        if type(v) == type:
            raise ValueError(f"Value Check Error: {k}:{v}")
        elif isinstance(v, BaseDataModel):
            v._check_value("%s(%s)" % (k, v.__class__.__name__), v.__dict__)
        elif isinstance(v, list):
            for i, p in enumerate(v):
                cls._check_value("%s[%s]" % (k, i), p)
        elif isinstance(v, dict):
            for _k, _v in v.items():
                cls._check_value("%s.%s" % (k, _k), _v)
        elif k in cls.DATA_DEFAULT_FORMAT and isinstance(cls.DATA_DEFAULT_FORMAT[k], BaseValueModel):
            cls.DATA_DEFAULT_FORMAT[k].apply(v)
        elif isinstance(v, LimitedValueModel):
            v.value()

    @classmethod
    def _to_dict(cls, k, v):
        '''转换成类JSON的dict对象'''
        if type(v) == type:
            raise ValueError(f"Type Check Error: {k}:{v}")
        else:
            try:
                if isinstance(v, BaseDataModel):
                    return v._to_dict("%s(%s)" % (k, v.__class__.__name__), v.__dict__)
                elif isinstance(v, list):
                    tmp = []
                    for i, p in enumerate(v):
                        tmp.append(cls._to_dict("%s[%s]" % (k, i), p))
                    return tmp
                elif isinstance(v, dict):
                    tmp = {}
                    for _k, _v in v.items():
                        tmp[_k] = cls._to_dict("%s.%s" % (k, _k), _v)
                    return tmp
                elif isinstance(v, BaseValueModel):
                    return cls._to_dict(k, v.value())
                return v
            except AssertionError as e:
                raise ValueError(f"AssertionError: {k}:{v}")

    def check(self):
        # 检查为type则抛出异常
        self._check_value("self", self.__dict__)
        return self

    def to_dict(self):
        return self._to_dict("self", self.__dict__)

    def to_json(self):
        return json.dumps(self.to_dict())

    EQUALS_IGNORE_KEYS = []

    @classmethod
    def _equals(cls, text, a, b):
        '''比较方法。可以考虑成 a == b，未覆盖底层__equal__'''
        if isinstance(a, BaseDataModel):
            assert sorted(list(a.__dict__.keys())) == sorted(list(b.keys())), f"{text} 数据长度不一致"
            for k, v in a.__dict__.items():
                if k not in a.EQUALS_IGNORE_KEYS:
                    if not cls._equals("%s[%s]" % (text, k), v, b[k]):
                        return False
            return True
        else:
            assert type(a) == type(b), f"{text} 无法验证数据格式"
            if isinstance(a, dict):
                assert sorted(list(a.keys())) == sorted(list(b.keys())), f"{text} 数据长度不一致"
                for k, v in a.items():
                    if not cls._equals("%s[%s]" % (text, k), v, b[k]):
                        return False
                return True
            elif isinstance(a, list):
                assert len(a) == len(b), f"{text} 数据长度不一致"
                for i, v in enumerate(a):
                    if not cls._equals("%s[%s]" % (text, i), v, b[i]):
                        return False
                return True
            else:
                return a == b

    # 数据对比. 忽略时间的影响
    def equals(self, data):
        assert isinstance(data, dict), "无法验证数据格式"
        return self._equals("self", self, data)


class BaseStrictDataModel(BaseDataModel):
    '''严格模式数据'''
    STRICT_MODE = True


class BaseExtraDictDataModel(BaseDataModel):
    def load_easy_data(self, db_dict):
        if isinstance(db_dict, dict):
            self.update(db_dict)
            return self
        return None


class BaseDBValueModel(BaseValueModel):
    '''用于标志能够表示数据的字段'''
    pass


class BaseDBDataModel(BaseExtraDictDataModel):
    '''支持数据库的单向映射 DB -> dict'''
    def load_db_data(self, *args, **kwargs):
        raise NotImplemented("未实现该方法")

    def is_exists(self):
        raise NotImplemented("未实现该方法")


class BaseMGDBDataModel(BaseDBDataModel):
    '''支持MongoDB互相映射'''
    def load_db_data(self, db_value, strict_mode=False):
        if isinstance(db_value, dict):
            for k, v in self.DATA_DEFAULT_FORMAT.items():
                if k in db_value:
                    if isinstance(v, BaseMGDBDataModel):
                        setattr(self, k, v.load_db_data(db_value.get(k), strict_mode))
                    elif v is BaseMGDBDataModel: # 存在
                        setattr(self, k, v().load_db_data(db_value.get(k), strict_mode))
                    else:
                        setattr(self, k, db_value.get(k))
        else:
            raise ValueError("不支持该数据类型:", db_value)
        return self


class CommDictModel(BaseDataModel):
    '''纯粹用于dict赋值。解释DATA_DEFAULT_FORMAT的values中{}代表dict。可以使用.xxx访问了'''
    STRICT_MODE = False # 必须是非严格模式



if __name__ == '__main__':
    b = BaseDataModel()
    print(vars(b))
    b.name = "dollar"

    print(vars(b))
    # print(getattr(b, "name"))
    # print(b.age)
    # print(b.name)
