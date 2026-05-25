import pyedb
import inspect

def run():
    edb = pyedb.Edb()
    fn = edb.cutout
    if hasattr(fn, '__wrapped__'):
        fn = fn.__wrapped__
    try:
        print(inspect.getsource(fn))
    except Exception as e:
        print(f"Error: {e}")
    edb.close()

if __name__ == "__main__":
    run()
