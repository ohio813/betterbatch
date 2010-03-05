#!python

if __name__ == '__main__':
    #import cProfile
    #import pstats

    try:
        Main()
        #cProfile.run('Main()', "profile_stats")
        #p = pstats.Stats('profile_stats')
        #p.sort_stats('cumulative').print_stats(10)

    except ErrorCollection, err:
        err.LogErrors()
    except RuntimeError, err:
        LOG.critical(err)
    except Exception, err:
        LOG.critical('Unknown Error: %s'% err)
        LOG.exception(err)
