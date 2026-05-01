# Adobe Lightroom Database Schema

Adobe Lightroom uses a SQLite database as its back-end.

## References

Most tables seem to have the following columns, **id_local** and **id_global**.

### id_local (INT)

This field is always an integer.

### id_global (STR)

This looks more like a GUID.

## Tables

* Full list of [Adobe Lightroom Database Tables](./tables.md)

### Adobe_images

``` text
+-----+------------------------+---------+---------+--------------+----+
| cid |          name          |  type   | notnull |  dflt_value  | pk |
+-----+------------------------+---------+---------+--------------+----+
|  0  |        id_local        | INTEGER |    0    |              | 1  |
|  1  |       id_global        |         |    1    |              | 0  |
|  2  |    aspectRatioCache    |         |    1    |      -1      | 0  |
|  3  |        bitDepth        |         |    1    |      0       | 0  |
|  4  |      captureTime       |         |    0    |              | 0  |
|  5  |     colorChannels      |         |    1    |      0       | 0  |
|  6  |      colorLabels       |         |    1    |      ''      | 0  |
|  7  |       colorMode        |         |    1    |      -1      | 0  |
|  8  |    copyCreationTime    |         |    1    | -63113817600 | 0  |
|  9  |        copyName        |         |    0    |              | 0  |
| 10  |       copyReason       |         |    0    |              | 0  |
| 11  | developSettingsIDCache |         |    0    |              | 0  |
| 12  |        editLock        | INTEGER |    1    |      0       | 0  |
| 13  |       fileFormat       |         |    1    |   'unset'    | 0  |
| 14  |       fileHeight       |         |    0    |              | 0  |
| 15  |       fileWidth        |         |    0    |              | 0  |
| 16  |   hasMissingSidecars   | INTEGER |    0    |              | 0  |
| 17  |      masterImage       | INTEGER |    0    |              | 0  |
| 18  |      orientation       |         |    0    |              | 0  |
| 19  |  originalCaptureTime   |         |    0    |              | 0  |
| 20  |   originalRootEntity   | INTEGER |    0    |              | 0  |
| 21  |    panningDistanceH    |         |    0    |              | 0  |
| 22  |    panningDistanceV    |         |    0    |              | 0  |
| 23  |          pick          |         |    1    |      0       | 0  |
| 24  |    positionInFolder    |         |    1    |     'z'      | 0  |
| 25  |    propertiesCache     |         |    0    |              | 0  |
| 26  |     pyramidIDCache     |         |    0    |              | 0  |
| 27  |         rating         |         |    0    |              | 0  |
| 28  |        rootFile        | INTEGER |    1    |      0       | 0  |
| 29  |     sidecarStatus      |         |    0    |              | 0  |
| 30  |       touchCount       |         |    1    |      0       | 0  |
| 31  |       touchTime        |         |    1    |      0       | 0  |
+-----+------------------------+---------+---------+--------------+----+
```

### AgLibraryFile

``` text
+-----+--------------------------+---------+---------+------------+----+
| cid |           name           |  type   | notnull | dflt_value | pk |
+-----+--------------------------+---------+---------+------------+----+
|  0  |         id_local         | INTEGER |    0    |            | 1  |
|  1  |        id_global         |         |    1    |            | 0  |
|  2  |         baseName         |         |    1    |     ''     | 0  |
|  3  |       errorMessage       |         |    0    |            | 0  |
|  4  |        errorTime         |         |    0    |            | 0  |
|  5  |        extension         |         |    1    |     ''     | 0  |
|  6  |     externalModTime      |         |    0    |            | 0  |
|  7  |          folder          | INTEGER |    1    |     0      | 0  |
|  8  |       idx_filename       |         |    1    |     ''     | 0  |
|  9  |        importHash        |         |    0    |            | 0  |
| 10  |     lc_idx_filename      |         |    1    |     ''     | 0  |
| 11  | lc_idx_filenameExtension |         |    1    |     ''     | 0  |
| 12  |           md5            |         |    0    |            | 0  |
| 13  |         modTime          |         |    0    |            | 0  |
| 14  |     originalFilename     |         |    1    |     ''     | 0  |
| 15  |    sidecarExtensions     |         |    0    |            | 0  |
+-----+--------------------------+---------+---------+------------+----+
```

The **folder** column matches the **id_local** column in the **AgLibraryFolder**
table:

``` sql
JOIN AgLibraryFolder
  ON AgLibraryFolder.id_local=AgLibraryFile.folder
```

### AgLibraryFolder

``` text
+-----+--------------+---------+---------+------------+----+
| cid |     name     |  type   | notnull | dflt_value | pk |
+-----+--------------+---------+---------+------------+----+
|  0  |   id_local   | INTEGER |    0    |            | 1  |
|  1  |  id_global   |         |    1    |            | 0  |
|  2  |   parentId   | INTEGER |    0    |            | 0  |
|  3  | pathFromRoot |         |    1    |     ''     | 0  |
|  4  |  rootFolder  | INTEGER |    1    |     0      | 0  |
|  5  |  visibility  | INTEGER |    0    |            | 0  |
+-----+--------------+---------+---------+------------+----+
```

The **rootFolder** column matches the **id_local** column in the
**AgLibraryRootFolder** table:

``` sql
JOIN AgLibraryRootFolder
  ON AgLibraryRootFolder.id_local=AgLibraryFolder.rootFolder
```

### AgLibraryRootFolder

``` text
+-----+-------------------------+---------+---------+------------+----+
| cid |          name           |  type   | notnull | dflt_value | pk |
+-----+-------------------------+---------+---------+------------+----+
|  0  |        id_local         | INTEGER |    0    |            | 1  |
|  1  |        id_global        |         |    1    |            | 0  |
|  2  |      absolutePath       |         |    1    |     ''     | 0  |
|  3  |          name           |         |    1    |     ''     | 0  |
|  4  | relativePathFromCatalog |         |    0    |            | 0  |
+-----+-------------------------+---------+---------+------------+----+
```

### Adobe_AdditionalMetadata

``` text
+-----+---------------------------+---------+---------+--------------+----+
| cid |           name            |  type   | notnull |  dflt_value  | pk |
+-----+---------------------------+---------+---------+--------------+----+
|  0  |         id_local          | INTEGER |    0    |              | 1  |
|  1  |         id_global         |         |    1    |              | 0  |
|  2  |     additionalInfoSet     | INTEGER |    1    |      0       | 0  |
|  3  |        embeddedXmp        | INTEGER |    1    |      0       | 0  |
|  4  |    externalXmpIsDirty     | INTEGER |    1    |      0       | 0  |
|  5  |           image           | INTEGER |    0    |              | 0  |
|  6  |  incrementalWhiteBalance  | INTEGER |    1    |      0       | 0  |
|  7  |     internalXmpDigest     |         |    0    |              | 0  |
|  8  |         isRawFile         | INTEGER |    1    |      0       | 0  |
|  9  |   lastSynchronizedHash    |         |    0    |              | 0  |
| 10  | lastSynchronizedTimestamp |         |    1    | -63113817600 | 0  |
| 11  |     metadataPresetID      |         |    0    |              | 0  |
| 12  |      metadataVersion      |         |    0    |              | 0  |
| 13  |        monochrome         | INTEGER |    1    |      0       | 0  |
| 14  |            xmp            |         |    1    |      ''      | 0  |
+-----+---------------------------+---------+---------+--------------+----+
```
