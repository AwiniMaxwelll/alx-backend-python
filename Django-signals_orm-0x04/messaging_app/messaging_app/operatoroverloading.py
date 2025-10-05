from pathlib import Path
# import math

# class Indexer:
#     def __init__(self, data:list):
#         self.data = data
    
#     def __getitem__(self, index:int):
#         print(f"index: {index}")
#         return self.data[index]
    
#     def __setitem__(self, index, value):
#         self.data[index] = value
    
#     def __index__(self):
#         return 10

# # s = Indexer([1, 2, 3, 4, 5, 10.5, 20, 30])
# # print(s[7:-1:2])
# # s[1] = 40
# # print(s.data)
# # print(bin(s))
# # # for x in s:
# # #     print(x)
# # print(1 in s)
# # x = list(map(math.ceil, s))
# # print(x)

# class Iter:
#     def __init__(self, start, stop):
#         self.value = start - 1
#         self.stop = stop
        
#     def __iter__(self):
#         return self
    
#     def __next__(self):
#         if self.value == self.stop:
#             raise StopIteration             
#         self.value += 1
#         return self.value ** 2

# i = Iter(0, 300)

# # for x in i:
# #     print(x, end=' ')

# def square(start, stop):
#     for x in range(start, stop+1):
#         yield x ** 3

# # for x in square(0, 10):
# #     print(x, end=', ')


# class SkipIterator:

#     def __init__(self, wrapper, step=1):
#         self.wrapper = wrapper
#         self.offset = 0
#         self.step = step
    
#     def __next__(self):
#         if self.offset >= len(self.wrapper):
#             raise StopIteration
#         value = self.wrapper[self.offset]
#         self.offset += self.step
#         return value
    
# class Stepper:
#     def __init__(self, wrapp, step=1) -> None:
#         self.wrapper = wrapp
#         self.step = step

#     def __iter__(self):
#         return SkipIterator(self.wrapper, self.step)
    

# skip = Stepper([1, 2, 3, 4, 10])
# for sk in skip:
#     for sk1 in skip:
#         print(sk * sk1, end=' ')


base = Path(__file__)
print(base.resolve().parent)