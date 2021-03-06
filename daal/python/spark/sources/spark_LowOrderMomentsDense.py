# file: spark_LowOrderMomentsDense.py
# ==============================================================
#
# SAMPLE SOURCE CODE - SUBJECT TO THE TERMS OF SAMPLE CODE LICENSE AGREEMENT,
# http://software.intel.com/en-us/articles/intel-sample-source-code-license-agreement/
#
# Copyright (C) Intel Corporation
#
# THIS FILE IS PROVIDED "AS IS" WITH NO WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT
# NOT LIMITED TO ANY IMPLIED WARRANTY OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE, NON-INFRINGEMENT OF INTELLECTUAL PROPERTY RIGHTS.
#
# =============================================================

#
#  Content:
#      Python sample of computing low order moments in the distributed
#      processing mode
#
from __future__ import print_function
import os
import sys

from pyspark import SparkContext, SparkConf

from daal import step1Local, step2Master
from daal.algorithms import low_order_moments

from distributed_hdfs_dataset import (
    DistributedHDFSDataSet, serializeNumericTable, deserializePartialResult, deserializeNumericTable
)

utils_folder = os.path.join(os.environ['DAALROOT'], 'examples', 'python', 'source')
if utils_folder not in sys.path:
    sys.path.insert(0, utils_folder)
from utils import printNumericTable


def runMoments(dataRDD):
    partsRDD = computestep1Local(dataRDD)
    return finalizeMergeOnMasterNode(partsRDD)


def computestep1Local(dataRDD):

    def mapper(tup):

        key, val = tup
        # Create an algorithm to compute low order moments on local nodes
        momentsLocal = low_order_moments.Distributed(step1Local, method=low_order_moments.defaultDense)

        # Set the input data on local nodes
        deserialized_val = deserializeNumericTable(val)
        momentsLocal.input.set(low_order_moments.data, deserialized_val)

        # Compute low order moments on local nodes
        pres = momentsLocal.compute()
        serialized_pres = serializeNumericTable(pres)

        return (key, serialized_pres)
    return dataRDD.map(mapper)


def finalizeMergeOnMasterNode(partsRDD):

    # Create an algorithm to compute low order moments on the master node
    momentsMaster = low_order_moments.Distributed(step2Master, method=low_order_moments.defaultDense)

    parts_List = partsRDD.collect()

    # Add partial results computed on local nodes to the algorithm on the master node
    for _, value in parts_List:
        deserialized_pres = deserializePartialResult(value, low_order_moments)
        momentsMaster.input.add(low_order_moments.partialResults, deserialized_pres)

    # Compute low order moments on the master node
    momentsMaster.compute()

    # Finalize computations and retrieve the results
    return momentsMaster.finalizeCompute()


if __name__ == "__main__":

    # Create SparkContext that loads defaults from the system properties and the classpath and sets the name
    sc = SparkContext(conf=SparkConf().setAppName("Spark low_order_moments(dense)").setMaster('local[4]'))

    # Read from the distributed HDFS data set at a specified path
    dd = DistributedHDFSDataSet("/Spark/LowOrderMomentsDense/data/")
    dataRDD = dd.getAsPairRDD(sc)

    # Compute low order moments for dataRDD
    res = runMoments(dataRDD)

    # Print the results
    minimum = res.get(low_order_moments.minimum)
    maximum = res.get(low_order_moments.maximum)
    sum = res.get(low_order_moments.sum)
    sumSquares = res.get(low_order_moments.sumSquares)
    sumSquaresCentered = res.get(low_order_moments.sumSquaresCentered)
    mean = res.get(low_order_moments.mean)
    secondOrderRawMoment = res.get(low_order_moments.secondOrderRawMoment)
    variance = res.get(low_order_moments.variance)
    standardDeviation = res.get(low_order_moments.standardDeviation)
    variation = res.get(low_order_moments.variation)

    # Redirect stdout to a file for correctness verification
    stdout = sys.stdout
    sys.stdout = open('LowOrderMomentsDense.out', 'w')

    print("Low order moments:")
    printNumericTable(minimum, "Min:")
    printNumericTable(maximum, "Max:")
    printNumericTable(sum, "Sum:")
    printNumericTable(sumSquares, "SumSquares:")
    printNumericTable(sumSquaresCentered, "SumSquaredDiffFromMean:")
    printNumericTable(mean, "Mean:")
    printNumericTable(secondOrderRawMoment, "SecondOrderRawMoment:")
    printNumericTable(variance, "Variance:")
    printNumericTable(standardDeviation, "StandartDeviation:")
    printNumericTable(variation, "Variation:")

    # Restore stdout
    sys.stdout = stdout

    sc.stop()
