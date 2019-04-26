import math
import statistics
from vtk import vtkMath
n = 43 # points sampled on grid

cutterPoints = getNode('C')
orderedGrid = []
row = []
for i in range(1, n):
    f = [0, 0, 0, 0]
    cutterPoints.GetNthFiducialWorldCoordinates(i-1, f)    
    row.append(f[:-1]) 
    if i  % 6 == 0:
        if len(orderedGrid) % 2 == 1:
            row.reverse()
        orderedGrid.append(row)
        row = []

rows = len(orderedGrid)
cols = len(orderedGrid[1])
distances = []

for i in range(rows):
    for j in range(1,cols):
        f1 = orderedGrid[i][j]
        f2 = orderedGrid[i][j-1]
        distance = math.sqrt(vtkMath.Distance2BetweenPoints(f1, f2))
        distances.append(distance)

for i in range(1,rows):
    for j in range(cols):
        f1 = orderedGrid[i-1][j]
        f2 = orderedGrid[i][j]
        distance = math.sqrt(vtkMath.Distance2BetweenPoints(f1, f2))
        distances.append(distance)

mean = sum(distances) / len(distances)
print 'Mean: ', mean
print 'Stdev: ', math.sqrt(sum(pow(x-mean,2) for x in distances) / len(distances)) # square root of variance


errors = [ math.abs(x - mean) for x in distances]
errorMean = sum(errors) /len(errors)
errorStdev = math.sqrt(sum(pow(x-mean,2) for x in errors) / len(errors))